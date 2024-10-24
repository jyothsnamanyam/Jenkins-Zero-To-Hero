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
                                        sandbox: false,
                                        script: 'please select Novartis bastion account type'
                                        ],
                                        script: [
                                        classpath: [],
                                        sandbox: false,
                                        script:
                                        """
                                            if(NVS_ENV_TYPE.equals('TEST')) {
                                                return ['BSTTST']
                                            }
                                            else if(NVS_ENV_TYPE.equals('PROD')) {
                                                return ['BST']
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
                                choiceType: 'ET_FORMATTED_HIDDEN_HTML',
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
                                            if(NVS_ACC_TYPE.equals('BSTTST')) {
                                                inputBox = "<input name='value' class='setting-input' type='text' value='636711886667'>"
                                            }
                                            else if(NVS_ACC_TYPE.equals('BST')) {
                                                inputBox = "<input name='value' class='setting-input' type='text' value='366103429990'>"
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
                                description: 'BST Primary region',
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
                                description: 'Lambda action to create or update the function.',
                                filterLength: 1,
                                filterable: false,
                                name: 'LAMBDA_ACTION',
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
                                    script: 'return[\'UPDATE\', \'CREATE\']'
                                    ]
                                ]
                            ],
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
        stage('Approval') {
             steps {
                 script {
                    timeout(time: 5, unit: 'MINUTES'){
                        input(id: "Deploy Approval", message: "Do you want to proceed for deployment in AWS REGION: ${params.RegionName} ?", ok: 'Deploy')
                    }
                 }
             }
         }
        stage('TGW VPC Acceptance Lambda Creation') {
            steps {
                script {
                    def rccAccountId = "304512965277"
                    def rccRole = rccAdmRole("${NVS_ENV_TYPE}")
                    rccAssume = assumeRole(rccAccountId, rccRole)
                    def targetAccountId = "${NVS_ACC_ID}"
                    def targetRole = bstAdmRole("${NVS_ENV_TYPE}")
                    targetAssume = assumeRole(targetAccountId, targetRole)
                    def bstrole = bstEwtpRole("${NVS_ENV_TYPE}")
                    bstAssume = assumeRole(targetAccountId, bstrole)
                    sh '''
                    python3 scripts/lambda_creation.py --environment=$NVS_ENV_TYPE --region_name=$RegionName --action=$LAMBDA_ACTION
                    '''
                }
            }
        }
    }
    post {
        success {
            script {

                println "Lambda creation was success."
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
                println "Lambda creation was failed."
            }
        }
    }
}

def assumeRole(AccountId, RoleName){
	println "Assuming ${RoleName} in account ${AccountId}."
	rccAdmJson = execSH("aws sts assume-role --role-arn arn:aws:iam::${AccountId}:role/${RoleName} --role-session-name ${RoleName}-sts --duration-second=3000")
	env.AWS_ACCESS_KEY_ID = rccAdmJson.Credentials.AccessKeyId
    env.AWS_SECRET_ACCESS_KEY = rccAdmJson.Credentials.SecretAccessKey
    env.AWS_SESSION_TOKEN = rccAdmJson.Credentials.SessionToken
}

def execSH(String command) {
    def getAccount = sh (
        script: command,
        returnStdout: true
    )
    return readJSON(text: getAccount)
}

def rccAdmRole(String str){
    def envType = str
    if (envType == "TEST"){
        def rccRole = "RCC_AWS_AUTOTST_ADM"
        return rccRole
    }else {
        def rccRole = "RCC_AWS_AUTO_ADM"
        return rccRole
    }
}

def bstAdmRole(String str){
    def envType = str
    if (envType == "TEST"){
        def bstRole = "RBSTTST_AWS_AUTOTST_ADM"
        return bstRole
    }else {
        def bstRole = "RBST_AWS_AUTO_ADM"
        return bstRole
    }
}

def bstEwtpRole(String str){
    def envType = str
    if (envType == "TEST"){
        def bstEwtpRole = "RBST_AWS_TSTAUTO_ADM"
        return bstEwtpRole
    }else {
        def bstEwtpRole = "RBST_AWS_EWTP_CONNECTIVITY"
        return bstEwtpRole
    }
}

def unSetAwsKeys(){
    env.AWS_ACCESS_KEY_ID = ""
    env.AWS_SECRET_ACCESS_KEY = ""
    env.AWS_SESSION_TOKEN = ""
}