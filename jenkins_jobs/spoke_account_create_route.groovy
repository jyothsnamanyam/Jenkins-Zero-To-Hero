import jenkins.model.*
import groovy.util.Node
import java.text.SimpleDateFormat

pipeline {
    agent any
    stages {
        stage('Setup parameters') {
            steps {
                script {
                    properties([
                        parameters([
                            [
                                $class: 'ChoiceParameter',
                                choiceType: 'PT_SINGLE_SELECT',
                                description: 'Novartis Environment type',
                                filterLength: 1,
                                filterable: false,
                                name: 'NVS_ENV_TYPE',
                                randomName: 'choice-parameter-73552873443119',
                                script: [
                                    $class: 'GroovyScript',
                                    fallbackScript: [
                                    classpath: [],
                                    sandbox: false,
                                    script: 'please select environment type'
                                    ],
                                    script: [
                                    classpath: [],
                                    sandbox: false,
                                    script:
                                    """
                                        import jenkins.model.Jenkins
                                        def url1 = Jenkins.instance.getRootUrl()
                                        if ( url1 == "https://aws-infra-cicd-prd.aws.novartis.net/" ){
                                            return['PROD']
                                        } else if ( url1 == "https://aws-infra-cicd-devtst.aws.novartis.net/" ){
                                            return['TEST']
                                        }
                                    """
                                    ]
                                ]
                            ],
                            [
                                $class: 'ChoiceParameter',
                                choiceType: 'PT_SINGLE_SELECT',
                                description: 'Region',
                                filterLength: 1,
                                filterable: false,
                                name: 'RegionName',
                                randomName: 'enc-choice-parameter-5663098801935',
                                script: [
                                        $class: 'GroovyScript',
                                        fallbackScript: [
                                        classpath: [],
                                        sandbox: false,
                                        script: ''
                                        ],
                                        script: [
                                        classpath: [],
                                        sandbox: true,
                                        script:
                                        """
										return ['ap-northeast-1']
										"""
                                        ]
                                    ]
                            ],
                            [
                                $class: 'ChoiceParameter',
                                choiceType: 'PT_SINGLE_SELECT',
                                description: 'SPOKE ACCOUNT TYPE, Ex: INTERNET.',
                                filterLength: 1,
                                filterable: false,
                                name: 'ACCOUNT_TYPE',
                                randomName: 'vpc-choice-parameter-5663098801699',
                                script: [
                                    $class: 'GroovyScript',
                                    fallbackScript: [
                                    classpath: [],
                                    sandbox: false,
                                    script: 'return[\'please select \']'
                                    ],
                                    script: [
                                    classpath: [],
                                    sandbox: true,
                                    script: 'return[\'INTRANET\', \'INTERNET\', \'ISOLATED\']'
                                    ]
                                ]
                            ],
                            [
                                $class: 'ChoiceParameter',
                                choiceType: 'PT_SINGLE_SELECT',
                                description: 'Please select The ROLE or IDY ROLE KEYS. ',
                                filterLength: 1,
                                filterable: false,
                                name: 'SPOKE_ACCESS_TYPE',
                                randomName: 'role-choice-parameter-5663098801655',
                                script: [
                                    $class: 'GroovyScript',
                                    fallbackScript: [
                                    classpath: [],
                                    sandbox: true,
                                    script: 'return[\'How you wants to access the resources\']'
                                    ],
                                    script: [
                                    classpath: [],
                                    sandbox: true,
                                    script: 'return[\'ROLE\', \'IDY_ROLE_KEYS\']'
                                    ]
                                ]
                            ],
                            [
                                $class: 'DynamicReferenceParameter',
                                choiceType: 'ET_FORMATTED_HTML',
                                omitValueField: true,
                                name: 'SPOKE_idy_accessKeyId',
                                randomName: 'access-56313144561786299',
                                referencedParameters: 'SPOKE_ACCESS_TYPE',
                                script: [
                                    $class: 'GroovyScript',
                                    fallbackScript: [
                                        classpath: [],
                                        sandbox: true,
                                        script:
                                            'return[\' SPOKE_accessKeyId\']'
                                    ],
                                    script: [
                                        classpath: [],
                                        sandbox: true,
                                        script:
                                        """
                                            if(SPOKE_ACCESS_TYPE.equals('IDY_ROLE_KEYS')) {
                                                inputBox = "<input name='value' class='setting-input' type='password'>"
                                            }
                                            else {
                                                inputBox="<input name='value' type='text' value='NA' disabled>"
                                            }
                                        """
                                    ]
                                ]
                            ],
							[
                                $class: 'DynamicReferenceParameter',
                                choiceType: 'ET_FORMATTED_HTML',
                                omitValueField: true,
                                name: 'SPOKE_idy_secretAccessKey',
                                randomName: 'secret-56313144561786288',
                                referencedParameters: 'SPOKE_ACCESS_TYPE',
                                script: [
                                    $class: 'GroovyScript',
                                    fallbackScript: [
                                        classpath: [],
                                        sandbox: true,
                                        script:
                                            'return[\' SPOKE_secretAccessKey\']'
                                    ],
                                    script: [
                                        classpath: [],
                                        sandbox: true,
                                        script:
                                        """
                                            if(SPOKE_ACCESS_TYPE.equals('IDY_ROLE_KEYS')) {
												inputBox = "<input name='value' class='setting-input' type='password'>"
                                            }
                                            else {
											inputBox="<input name='value' type='text' value='NA' disabled>"
                                            }
                                        """
                                    ]
                                ]
                            ],
							[
                                $class: 'DynamicReferenceParameter',
                                choiceType: 'ET_FORMATTED_HTML',
                                omitValueField: true,
                                name: 'SPOKE_idy_sessionToken',
                                randomName: 'token-56313144561786277',
                                referencedParameters: 'SPOKE_ACCESS_TYPE',
                                script: [
                                    $class: 'GroovyScript',
                                    fallbackScript: [
                                        classpath: [],
                                        sandbox: true,
                                        script:
                                            'return[\' SPOKE_sessionToken\']'
                                    ],
                                    script: [
                                        classpath: [],
                                        sandbox: true,
                                        script:
                                        """
                                            if(SPOKE_ACCESS_TYPE.equals('IDY_ROLE_KEYS')) {
												inputBox = "<input name='value' class='setting-input' type='password'>"
                                            }
                                            else {
											inputBox="<input name='value' type='text' value='NA' disabled>"
                                            }
                                        """
                                    ]
                                ]
                            ],
                            [
                                $class: 'DynamicReferenceParameter',
                                choiceType: 'ET_FORMATTED_HTML',
                                omitValueField: true,
                                name: 'SPOKE_idy_role_name',
                                randomName: 'token-56313144561786266',
                                referencedParameters: 'SPOKE_ACCESS_TYPE',
                                script: [
                                    $class: 'GroovyScript',
                                    fallbackScript: [
                                        classpath: [],
                                        sandbox: true,
                                        script:
                                            'return[\' SPOKE_role name\']'
                                    ],
                                    script: [
                                        classpath: [],
                                        sandbox: true,
                                        script:
                                        """
                                            if(SPOKE_ACCESS_TYPE.equals('IDY_ROLE_KEYS')) {
												inputBox = "<input name='value' class='setting-input' type='text' value='', placeholder='RIDY_AWS_AWSGLOBALJIT01'>"
                                            }
                                            else {
											inputBox="<input name='value' type='text' value='NA' disabled>"
                                            }
                                        """
                                    ]
                                ]
                            ]
                        ])
                    ])
                }
            }
        }

		stage('Check Parameters') {
             steps {
                 script {
                     params.each { param ->
                           //println " '${param.key.trim()}' -> '${param.value.trim()}' "
                           if (param.value.isEmpty()){
                             currentBuild.result = 'ABORTED'
                             println "Please add missing parameter ${param.key.trim()}"
                             error( 'All parameters are must be provided')
                           }
                     }
                 }
             }
         }

        stage('Approval') {
             steps {
                 script {
                    timeout(time: 5, unit: 'MINUTES'){
                        input(id: "Deploy Approval", message: "Do you want to proceed for deployment in AWS REGION: ${params.RegionName} ?", ok: 'Deploy')
                    }
                 }
             }
         }

        stage('Spoke vpc routing rules.') {
            steps {
                script {
                    sh '''
                    python3 scripts/spoke_account_create_route.py --env_type=$NVS_ENV_TYPE --region_name=$RegionName --account_type=$ACCOUNT_TYPE --access_type=$SPOKE_ACCESS_TYPE
                    '''
                }
            }
        }
    }
    post {
        success {
            script {

                println "Routing rules creation was success."
                def cause = currentBuild.getBuildCauses('hudson.model.Cause$UserIdCause')
                env.userId = cause.userId[0]
                env.userName = cause.userName[0]
                def d = new Date()
                def sdf = new SimpleDateFormat ("yyyy-MM-dd HH:mm:ss")
                sdf.setTimeZone(TimeZone.getTimeZone("IST"))
                env.currentBuildTime = sdf.format(d)
                sh '''
                echo "Success"
                '''
            }
        }
        failure {
            script {
                println "spoke account check was failed."
            }
        }
    }
}

