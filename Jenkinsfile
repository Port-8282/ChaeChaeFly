pipeline {
    agent { label 'ci-docker' }
    options {
        skipDefaultCheckout(true)
        disableConcurrentBuilds()
        timestamps()
        timeout(time: 45, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10', artifactNumToKeepStr: '10'))
    }
    stages {
        stage('Checkout') {
            steps {
                deleteDir()
                checkout scm
            }
        }
        stage('CI environment') {
            steps { sh 'python3 infra/scripts/ci.py init' }
        }
        stage('Compose validation') {
            steps { sh 'python3 infra/scripts/ci.py config' }
        }
        stage('Front build') {
            steps { sh 'python3 infra/scripts/ci.py front' }
        }
        stage('Back build and tests') {
            steps { sh 'python3 infra/scripts/ci.py back' }
        }
        stage('AI checks') {
            steps { sh 'python3 infra/scripts/ci.py ai' }
        }
        stage('ML checks') {
            steps { sh 'python3 infra/scripts/ci.py ml' }
        }
        stage('Runtime smoke') {
            steps { sh 'python3 infra/scripts/ci.py smoke' }
        }
    }
    post {
        always {
            script {
                if (fileExists('infra/scripts/ci.py')) {
                    catchError(buildResult: 'FAILURE', stageResult: 'FAILURE') {
                        sh 'python3 infra/scripts/ci.py cleanup'
                    }
                }
            }
            junit testResults: 'ci-results/**/*.xml', allowEmptyResults: true
            archiveArtifacts artifacts: 'ci-results/**/*.xml,ci-results/*.log,ci-results/summary.json', allowEmptyArchive: true
        }
    }
}
