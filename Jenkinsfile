pipeline {
    agent any

    stages {
        stage('Install') {
            steps {
                sh 'python3 -m venv .venv'
                sh '. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt'
            }
        }
        stage('Test') {
            steps {
                sh '. .venv/bin/activate && pytest'
            }
        }
        stage('Build Image') {
            steps {
                sh 'docker build -t appointment-service:latest .'
            }
        }
    }
}
