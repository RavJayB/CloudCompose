Now check this - 

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

    stage('Notify GitHub Start') {
      steps {
        step([$class: 'GitHubCommitStatusSetter',
          contextSource: [$class: 'ManuallyEnteredCommitContextSource', context: 'jenkins'],
          statusResultSource: [$class: 'DefaultStatusResultSource'],
          statusBackrefSource: [$class: 'BuildRefBackrefSource']
        ])
      }
    }


    stage('Preflight') {
      when {
        allOf {
          branch 'main'
          not { changeRequest() }
        }
      }
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

        script {
          step([$class: 'GitHubCommitStatusSetter',
            contextSource: [$class: 'ManuallyEnteredCommitContextSource', context: 'ci/jenkins/tests'],
            statusResultSource: [$class: 'DefaultStatusResultSource'],
            statusBackrefSource: [$class: 'BuildRefBackrefSource']
          ])
        }
        sh '''
          set -e
          docker run --rm -v "$WORKSPACE/api":/app -w /app \
          python:3.12-slim bash -lc \
          "pip install -r requirements.txt -r requirements-dev.txt && pytest -q"
        '''
      }
    }

    stage('Login to ECR') {
      when {
        allOf {
          branch 'main'
          not { changeRequest() }
        }
      }

      steps {
        // If Jenkins has an instance role, no credentials needed — just run aws cli.
        sh '''
          set -e
          aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $REGISTRY_URL
        '''
      }
    }

    stage("Build and push API Image") {
      when {
        allOf {
          branch 'main'
          not { changeRequest() }
        }
      }
      steps {

        script {
          step([$class: 'GitHubCommitStatusSetter',
            contextSource: [$class: 'ManuallyEnteredCommitContextSource', context: 'ci/jenkins/build'],
            statusResultSource: [$class: 'DefaultStatusResultSource'],
            statusBackrefSource: [$class: 'BuildRefBackrefSource']
          ])
        }

        sh '''
          set -e

          IMAGE_BUILD_TAG=build-${BUILD_NUMBER}
          IMAGE_GIT_TAG=git-${GIT_COMMIT}

          docker build \
            -t $ECR_API:latest \
            -t $ECR_API:$IMAGE_BUILD_TAG \
            -t $ECR_API:$IMAGE_GIT_TAG \
            ./api

          docker push $ECR_API:latest
          docker push $ECR_API:$IMAGE_BUILD_TAG
          docker push $ECR_API:$IMAGE_GIT_TAG
        '''
      }
    }


   stage('Build & Push Nginx') {
      when {
        allOf {
          branch 'main'
          not { changeRequest() }
        }
      }
      steps {

        script {
          step([$class: 'GitHubCommitStatusSetter',
            contextSource: [$class: 'ManuallyEnteredCommitContextSource', context: 'ci/jenkins/build'],
            statusResultSource: [$class: 'DefaultStatusResultSource'],
            statusBackrefSource: [$class: 'BuildRefBackrefSource']
          ])
        }

        sh '''
          set -e

          IMAGE_BUILD_TAG=build-${BUILD_NUMBER}
          IMAGE_GIT_TAG=git-${GIT_COMMIT}

          docker build \
            -t $ECR_NGINX:latest \
            -t $ECR_NGINX:$IMAGE_BUILD_TAG \
            -t $ECR_NGINX:$IMAGE_GIT_TAG \
            ./nginx

          docker push $ECR_NGINX:latest
          docker push $ECR_NGINX:$IMAGE_BUILD_TAG
          docker push $ECR_NGINX:$IMAGE_GIT_TAG
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
      when {
        allOf {
          branch 'main'
          not { changeRequest() }
        }
      }
      options { timeout(time: 10, unit: 'MINUTES') }
      steps {

        script {
          step([$class: 'GitHubCommitStatusSetter',
            contextSource: [$class: 'ManuallyEnteredCommitContextSource', context: 'ci/jenkins/deploy'],
            statusResultSource: [$class: 'DefaultStatusResultSource'],
            statusBackrefSource: [$class: 'BuildRefBackrefSource']
          ])
        }

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
              ssh -o StrictHostKeyChecking=no \
                -o ServerAliveInterval=60 \
                -o ServerAliveCountMax=3 \
                ubuntu@${APP_HOST_IP} \
                "mkdir -p ~/compose-fullstack"

              # 2. Copy compose file
              scp \
                -o StrictHostKeyChecking=no \
                -o ConnectTimeout=10 \
                -o ServerAliveInterval=60 \
                -o ServerAliveCountMax=3 \
                "$WORKSPACE/docker-compose.yaml" \
                ubuntu@${APP_HOST_IP}:/home/ubuntu/compose-fullstack/

              # 3. Run deployment remotely
              ssh \
                -o StrictHostKeyChecking=no \
                -o ServerAliveInterval=60 \
                -o ServerAliveCountMax=3 \
                ubuntu@${APP_HOST_IP} "
                set -e
                export IMAGE_TAG=build-${BUILD_NUMBER}
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
                docker compose ps
                docker image prune -f

              "
            '''
          }
        }
      }
    }
  }

  // post {
  //   success {
  //     step([$class: 'GitHubCommitStatusSetter',
  //       contextSource: [$class: 'ManuallyEnteredCommitContextSource', context: 'jenkins'],
  //       statusResultSource: [$class: 'DefaultStatusResultSource'],
  //       statusBackrefSource: [$class: 'BuildRefBackrefSource']
  //     ])
  //   }

  //   failure {
  //     step([$class: 'GitHubCommitStatusSetter',
  //       contextSource: [$class: 'ManuallyEnteredCommitContextSource', context: 'jenkins'],
  //       statusResultSource: [$class: 'DefaultStatusResultSource'],
  //       statusBackrefSource: [$class: 'BuildRefBackrefSource']
  //     ])
  //     echo "Build failed - check logs"
  //   }
  // }

}