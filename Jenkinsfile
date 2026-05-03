pipeline {
    agent {
        docker {
            image 'python:3.10'
            args '-u root'
        }
    }

    stages {

        stage('Clone Repository') {
            steps {
                deleteDir()
                git branch: 'main', url: 'https://github.com/himanipilankar18/Driver-drowsiness-Web-App--devops-project.git'
            }
        }

        stage('Install Dependencies') {
            steps {
                sh '''
                python -m venv venv
                . venv/bin/activate
                pip install -r requirements.txt 
                '''
            }
        }

        stage('Run Tests') {
            steps {
                sh '''
                . venv/bin/activate
                PYTHONPATH=. pytest tests/test_api.py
                '''
            }
        }

        stage('Build Docker Image') {
            steps {
                sh 'docker build -t driver-safety-app .'
            }
        }

        stage('Push to DockerHub') {
            steps {
                withCredentials([usernamePassword(
                    credentialsId: 'dockerhub-creds',
                    usernameVariable: 'DOCKER_USER',
                    passwordVariable: 'DOCKER_PASS'
                )]) {
                    sh '''
                    echo "$DOCKER_PASS" | docker login -u "$DOCKER_USER" --password-stdin
                    docker tag driver-safety-app himanipilankar/driver-safety-app:latest
                    docker push himanipilankar/driver-safety-app:latest
                    '''
                }
            }
        }
    }
}
