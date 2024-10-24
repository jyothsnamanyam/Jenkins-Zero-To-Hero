import groovy.json.JsonSlurperClassic
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
                                $class: 'CascadeChoiceParameter',
                                choiceType: 'PT_SINGLE_SELECT',
                                description: 'Novartis bastion account type',
                                filterLength: 1,
                                filterable: false,
                                name: 'NVS_ACC_TYPE',
                                randomName: 'choice-parameter-73552873443120',
                                referencedParameters: 'NVS_ENV_TYPE',
                                script: [
                                        $class: 'GroovyScript',
                                        fallbackScript: [
                                        classpath: [],
                                        sandbox: true,
                                        script: 'please select Novartis bastion account type'
                                        ],
                                        script: [
                                        classpath: [],
                                        sandbox: true,
                                        script:
                                        """
                                            if(NVS_ENV_TYPE.equals('TEST')) {
                                                return ['DMZTST']
                                            }
                                            else if(NVS_ENV_TYPE.equals('PROD')) {
                                                return ['DMZ']
                                            }
                                            else {
                                                return ['NA']
                                            }
                                        """
                                        ]
                                    ]
                            ],
                            [
                                $class: 'DynamicReferenceParameter',
                                choiceType: 'ET_FORMATTED_HTML',
                                omitValueField: true,
                                description: 'Please enter the Novartis Source Account ID. ',
                                name: 'NVS_ACC_ID',
                                randomName: 'config-parameter-56313144561786258',
                                referencedParameters: 'NVS_ACC_TYPE',
                                script: [
                                    $class: 'GroovyScript',
                                    fallbackScript: [
                                        classpath: [],
                                        sandbox: true,
                                        script:
                                            'return[\'Please enter the Novartis Source Account ID.\']'
                                    ],
                                    script: [
                                        classpath: [],
                                        sandbox: true,
                                        script:
                                        """
                                            if(NVS_ACC_TYPE.equals('DMZTST')) {
                                                inputBox = "<input name='value' class='setting-input' type='text' value='728756811910'>"
                                            }
                                            else if(NVS_ACC_TYPE.equals('DMZ')) {
                                                inputBox = "<input name='value' class='setting-input' type='text' value='132910123013'>"
                                            }
                                            else {
                                                inputBox="<input name='value' type='text' value='NA' disabled>"
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
                           println " '${param.key.trim()}' -> '${param.value.trim()}' "
                           if (param.value.isEmpty()){
                             currentBuild.result = 'ABORTED'
                             println "Please add missing parameter ${param.key.trim()}"
                             error( 'All parameters are must be provided')
                           }
                     }
                 }
             }
         }
        /*
        stage('Approval') {
             steps {
                 script {
                    timeout(time: 5, unit: 'MINUTES'){
                        input(id: "Deploy Approval", message: "Do you want to proceed for deployment in AWS REGION: ${params.RegionName} ?", ok: 'Deploy')
                    }
                 }
             }
         }
        */
        stage('DMZ NAT VPC SPOKE AUTOMATION') {
            steps {
                script {
                    sh '''
                    python3 scripts/dmz_nat_vpc_spoke_automation.py --env_type=$NVS_ENV_TYPE --region_name=$RegionName
                    '''
                }
            }
        }
    }

    post {
        success {
            script {
                println "DMZ NAT Spoke VPCs attachment was success."
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
                println "DMZ, NAT Spoke VPCs attachments was failed."
            }
        }
    }

}



