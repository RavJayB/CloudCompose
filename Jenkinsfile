pipeline {
  agent any

  environment {
    IMAGE_NAME = "ravjayb/compose-fullstack-api"
  }

  stages {

    stage("Checkout") {
      steps {
        checkout scm
      }
    }

    stage("Build Docker Image") {
      steps {
        sh '''
          docker build -t $IMAGE_NAME:latest ./api
        '''
      }
    }

    stage("DockerHub Login") {
      steps {
        withCredentials([usernamePassword(credentialsId: 'dockerhub-creds', usernameVariable: 'DOCKER_USER', passwordVariable: 'DOCKER_PASS')]) {
          sh '''
            echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
          '''
        }
      }
    }

    stage("Push Image") {
      steps {
        sh '''
          docker push $IMAGE_NAME:latest
        '''
      }
    }

    stage("Deploy") {
      steps {
        sh '''
          cd $WORKSPACE
          docker compose pull
          docker compose up -d
        '''
      }
    }
  }
}
