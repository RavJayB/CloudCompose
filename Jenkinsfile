pipeline {
  agent any

  environment {
    // AWS_ACCOUNT = "${env.AWS_ACCOUNT ?: ''}"
    REGION = 'ap-south-1'
    // APP_HOST_IP = 'YOUR-EC2-B-IP' <-- configured this as jenkins parameter, so it can be set at build time
    ECR_API = "270099212260.dkr.ecr.ap-south-1.amazonaws.com/compose-fullstack-api"
    ECR_NGINX = "270099212260.dkr.ecr.ap-south-1.amazonaws.com/compose-fullstack-nginx"
    REGISTRY_URL = "270099212260.dkr.ecr.ap-south-1.amazonaws.com"
  }

  stages {

    stage('Preflight') {
      steps {
        script {
          if (!env.APP_HOST_IP?.trim()) {
            error "APP_HOST_IP parameter is required but not set."
          }
        }
      }
    }

    stage("Checkout") {
      steps {
        checkout scm
        script {
          if(!env.GIT_COMMIT) {
            env.GIT_COMMIT = sh(script: "git rev-parse --short HEAD", returnStdout: true).trim()
          }
          echo "Using GIT_COMMIT: ${env.GIT_COMMIT}"
        }
      }
    }

    // Run tests in a container to ensure consistent environment 
    stage('Run tests') {
      steps {
        sh '''
          set -e
          docker run --rm -v "$WORKSPACE/api":/app -w /app \
          python:3.12-slim bash -lc \
          "pip install -r requirements.txt -r requirements-dev.txt && pytest -q"
        '''
      }
    }

    stage('Login to ECR') {
      steps {
        // If Jenkins has an instance role, no credentials needed — just run aws cli.
        sh '''
          set -e
          aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $REGISTRY_URL
        '''
      }
    }

    stage("Build and push API Image") {
      steps {
        sh '''
          set -e 
          docker build -t $ECR_API:$GIT_COMMIT ./api
          docker push $ECR_API:$GIT_COMMIT
          docker tag $ECR_API:$GIT_COMMIT $ECR_API:latest
          docker push $ECR_API:latest 
          '''
      }
    }

   stage('Build & Push Nginx') {
     steps {
       sh '''
         set -e
         docker build -t $ECR_NGINX:$GIT_COMMIT ./nginx
         docker push $ECR_NGINX:$GIT_COMMIT
         docker tag $ECR_NGINX:$GIT_COMMIT $ECR_NGINX:latest
         docker push $ECR_NGINX:latest 
       '''
     }
   }

   stage('Docker cleanup') {
      steps {
        sh '''
          docker image prune -f
          docker builder prune -f
        '''
      }
    }

    stage('Deploy to EC2-B') {
      steps {
        sshagent(credentials: ['SSH']) {
          withCredentials([
            string(credentialsId: 'pg-db-name', variable: 'POSTGRES_DB'),
            string(credentialsId: 'pg-db-user', variable: 'POSTGRES_USER'),
            string(credentialsId: 'pg-db-password', variable: 'POSTGRES_PASSWORD')
          ]) {
            sh '''
              set -e
              echo "Deploying to EC2-B at ${APP_HOST_IP}"

              # 1. Ensure directory exists
              ssh -o StrictHostKeyChecking=no ubuntu@${APP_HOST_IP} \
                "mkdir -p ~/compose-fullstack"

              # 2. Copy compose file
              scp -o StrictHostKeyChecking=no -o ConnectTimeout=10 \
                $WORKSPACE/docker-compose.yaml \
                ubuntu@${APP_HOST_IP}:/home/ubuntu/compose-fullstack/

              # 3. Run deployment remotely
              ssh -o StrictHostKeyChecking=no ubuntu@${APP_HOST_IP} "
                set -e
                export IMAGE_TAG=${GIT_COMMIT}
                export ECR_API=${ECR_API}
                export ECR_NGINX=${ECR_NGINX}
                export POSTGRES_DB=${POSTGRES_DB}
                export POSTGRES_USER=${POSTGRES_USER}
                export POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

                cd ~/compose-fullstack || exit 1

                aws ecr get-login-password --region ${REGION} | \
                  docker login --username AWS --password-stdin ${REGISTRY_URL}

                docker compose pull
                docker compose up -d --remove-orphans
                docker image prune -f

              "
            '''
          }
        }
      }
    }
  }

  post {
      failure {
        echo "Build failed - check logs"
      }
    } 
}
