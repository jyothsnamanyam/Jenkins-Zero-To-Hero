pipeline {
    agent any

    parameters {
        string(name: 'ACCOUNT_ID', defaultValue: '', description: 'AWS Account Number')
        string(name: 'AWS_ACCESS_KEY_ID', defaultValue: '', description: 'AWS Access Key ID')
        string(name: 'AWS_SECRET_ACCESS_KEY', defaultValue: '', description: 'AWS Secret Access Key')
        string(name: 'AWS_SESSION_TOKEN', defaultValue: '', description: 'AWS Session Token')
        string(name: 'ASSUME_ROLE_NAME', defaultValue: '', description: 'AWS Assume Role Name')
        string(name: 'AWS_REGION', defaultValue: 'us-west-2', description: 'AWS Region')
    }

    environment {
        SCRIPT_PATH = 'scripts/delete_unused_volumes_updated.py'
        AWS_ACCESS_KEY_ID = "${params.AWS_ACCESS_KEY_ID}"
        AWS_SECRET_ACCESS_KEY = "${params.AWS_SECRET_ACCESS_KEY}"
        AWS_SESSION_TOKEN = "${params.AWS_SESSION_TOKEN}"
    }

    stages {
        stage('Checkout') {
            steps {
                // Checkout the code from the Git repository
                git url: 'ssh://git@bitbucketenterprise.aws.novartis.net/tisce/ewtp-fw-security-stack.git', 
                    branch: 'aws-volume',
                    credentialsId: 'BitbucketKey'
            }
        }

        stage('Install Dependencies') {
            steps {
                // Install required Python packages
                sh 'pip3 install boto3'
            }
        }

        stage('Approval') {
            steps {
                script {
                    timeout(time: 5, unit: 'MINUTES') {
                        def userInput = input(
                            id: 'DeployApproval', 
                            message: "Do you want to proceed with the deployment for account: ${params.ACCOUNT_NAME} in region: ${params.AWS_REGION}?",
                            parameters: [
                                [$class: 'ChoiceParameterDefinition', choices: ['Approve', 'Reject'].join('\n'), description: 'Choose Approve or Reject', name: 'Decision']
                            ]
                        )
                        if (userInput == 'Reject') {
                            error("Deployment rejected by user.")
                        }
                    }
                }
            }
        }

        stage('Execute Script') {
            steps {
                // Execute the Python script with the provided parameters   
              sh """
                python3 ${env.SCRIPT_PATH} \
                --account-id ${params.ACCOUNT_ID} \
                --access-key ${env.AWS_ACCESS_KEY_ID} \
                --secret-key ${env.AWS_SECRET_ACCESS_KEY} \
                --session-token ${env.AWS_SESSION_TOKEN} \
                --aws-assume-role-name ${params.ASSUME_ROLE_NAME} \
                --region ${params.AWS_REGION}
                """
            }
        }
    }

    post {
        always {
            echo 'Pipeline execution finished.'
        }
    }
}
