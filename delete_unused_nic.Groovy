pipeline {
    agent any

    parameters {
        string(name: 'AWS_ACCESS_KEY_ID', defaultValue: '', description: 'AWS Access Key ID')
        string(name: 'AWS_SECRET_ACCESS_KEY', defaultValue: '', description: 'AWS Secret Access Key')
        string(name: 'AWS_SESSION_TOKEN', defaultValue: '', description: 'AWS Session Token')
        string(name: 'CONFIG_FILE_PATH', defaultValue: 'config/accounts_config.json', description: 'Path to the accounts configuration JSON file')
    }

    environment {
        SCRIPT_PATH = 'scripts/delete_unused_nic.py'
        AWS_ACCESS_KEY_ID = "${params.AWS_ACCESS_KEY_ID}".trim().replaceAll('^"|"$', '')
        AWS_SECRET_ACCESS_KEY = "${params.AWS_SECRET_ACCESS_KEY}".trim().replaceAll('^"|"$', '')
        AWS_SESSION_TOKEN = "${params.AWS_SESSION_TOKEN}".trim().replaceAll('^"|"$', '')
    }

    stages {
        stage('Checkout') {
            steps {
                // Checkout the code from the Git repository
                git url: 'ssh://git@bitbucketenterprise.aws.novartis.net/tisce/one-design.git',
                    branch: 'develop-china',  // Adjust the branch name as needed
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
                            message: "Do you want to proceed with the deletion of unused Network Interfaces?",
                            parameters: [
                                [$class: 'ChoiceParameterDefinition', choices: ['Approve', 'Reject'].join('\n'), description: 'Choose Approve or Reject', name: 'Decision']
                            ]
                        )
                        if (userInput == 'Reject') {
                            error("Deletion rejected by user.")
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
                --access-key '${env.AWS_ACCESS_KEY_ID}' \
                --secret-key '${env.AWS_SECRET_ACCESS_KEY}' \
                --session-token '${env.AWS_SESSION_TOKEN}' \
                --config-file '${params.CONFIG_FILE_PATH}'
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
