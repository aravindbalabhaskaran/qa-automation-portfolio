// Declarative pipeline for a Jenkins agent that has Python 3.10+ and Node 18+.
pipeline {
    agent any
    options { timestamps(); timeout(time: 20, unit: 'MINUTES') }
    environment { ARTIFACTS_DIR = 'artifacts' }

    stages {
        stage('Install') {
            steps {
                sh '''
                    python3 -m venv .venv
                    . .venv/bin/activate
                    pip install -r requirements.txt
                    playwright install --with-deps chromium
                '''
            }
        }
        stage('Smoke') {
            steps {
                sh '. .venv/bin/activate && pytest -m smoke --junitxml=reports/smoke.xml'
            }
        }
        stage('Regression') {
            steps {
                sh '. .venv/bin/activate && pytest --junitxml=reports/regression.xml'
            }
        }
        stage('Postman / Newman') {
            steps {
                sh '''
                    . .venv/bin/activate
                    python -m demo_app & APP_PID=$!
                    for i in $(seq 1 30); do curl -sf http://127.0.0.1:5000/api/health && break || sleep 1; done
                    npx --yes newman run postman/parts-shop.postman_collection.json \
                        -e postman/local.postman_environment.json \
                        --reporters cli,junit --reporter-junit-export reports/newman.xml
                    STATUS=$?
                    kill $APP_PID
                    exit $STATUS
                '''
            }
        }
    }
    post {
        always {
            junit allowEmptyResults: true, testResults: 'reports/*.xml'
            archiveArtifacts artifacts: 'artifacts/**', allowEmptyArchive: true
        }
    }
}
