#!groovy

pipeline {

  // agent defines where the pipeline will run.
  agent {  
    label {
      label "genie"
    }
  }
  
  environment {
      NODE = "${env.NODE_NAME}"
      PLOCK = "python_${NODE}"
  }
  
  triggers {
    pollSCM('H/2 * * * *')
  }

  // The options directive is for configuration that applies to the whole job.
  options {
    buildDiscarder(logRotator(numToKeepStr:'5', daysToKeepStr: '7'))
    disableConcurrentBuilds()
    timestamps()
    office365ConnectorWebhooks([[
                    name: "Office 365",
                    notifyBackToNormal: true,
                    startNotification: false,
                    notifyFailure: true,
                    notifySuccess: false,
                    notifyNotBuilt: false,
                    notifyAborted: false,
                    notifyRepeatedFailure: true,
                    notifyUnstable: true,
                    url: "${env.MSTEAMS_URL}"
            ]]
    )
  }

  stages {  
    stage("Checkout") {
      steps {
        timeout(time: 2, unit: 'HOURS') {
          retry(5) {
            echo "Branch: ${env.BRANCH_NAME}"
            checkout scm
          }
        }
      }
   }
    
    stage("Build for Python 3") {
      steps {
        echo "Build Number: ${env.BUILD_NUMBER}"
        lock(resource: PLOCK, inversePrecedence: false) {
        timeout(time: 120, unit: 'MINUTES') {
        script {
            env.GIT_COMMIT = bat(returnStdout: true, script: '@git rev-parse HEAD').trim()
            env.GIT_BRANCH = bat(returnStdout: true, script: '@git rev-parse --abbrev-ref HEAD').trim()
            echo "git commit: ${env.GIT_COMMIT}"
            echo "git branch: ${env.BRANCH_NAME} ${env.GIT_BRANCH}"
            // env.BRANCH_NAME is only supplied to multi-branch pipeline jobs
            if (env.BRANCH_NAME == null) {
                env.BRANCH_NAME = "master"
            }

            if (env.BRANCH_NAME != null && env.BRANCH_NAME.startsWith("Release")) {
                env.IS_RELEASE = "YES"
                env.RELEASE_VERSION = "${env.BRANCH_NAME}".replace('Release_', '')
                echo "release version: ${env.RELEASE_VERSION}"
            }
            else {
                env.IS_RELEASE = "NO"
                env.RELEASE_VERSION = ""
            }
        }
        bat """
            git clean -fqdx
            set BUILD_NUMBER=${env.BUILD_NUMBER}
            set BRANCH_NAME=${env.BRANCH_NAME}
            set GIT_COMMIT=${env.GIT_COMMIT}
            set RELEASE_BRANCH=${env.RELEASE_VERSION}
            set RELEASE=${env.IS_RELEASE}
            cd package_builder
            jenkins_build_python.bat 3
            """
        }
        }
      }
    }
    stage("Report Unit Tests python 3") {
      steps {
        junit '**/test-reports/TEST-*.xml'
      }
   }
    stage("Trigger Downstream") {
      steps {
        build job: 'ibex_gui_pipeline', wait: false
      }
    }
  }
  post {
    cleanup {
            echo "***"
            echo "*** Any Office365connector Matched status FAILURE message below means"
            echo "*** an earlier Jenkins step failed not the Office365connector itself"
            echo "*** Search log file for  ERROR  to locate true cause"
            echo "***"
    }
    always {
        logParser ([
                projectRulePath: 'parse_rules',
                parsingRulesPath: '',
                showGraphs: true,
                unstableOnWarning: false,
                useProjectRule: true,
            ])
    }
  }
}
