#!groovy

pipeline {

  // agent defines where the pipeline will run.
  agent {  
    label {
      label "genie"
      // Use custom workspace to avoid issue with long filepaths on Win32
      customWorkspace "C:/genie/${BRANCH_NAME}"
    }
  }
  
  triggers {
    pollSCM('H/2 * * * *')
  }
  
  stages {  
    stage("Checkout") {
      steps {
        echo "Branch: ${env.BRANCH_NAME}"
        checkout scm
      }
    }
    
    stage("Build") {
      steps {
        echo "Build Number: ${env.BUILD_NUMBER}"
        script {
            env.GIT_COMMIT = bat(returnStdout: true, script: '@git rev-parse HEAD').trim()
            env.GIT_BRANCH = bat(returnStdout: true, script: '@git rev-parse --abbrev-ref HEAD').trim()
            echo "git commit: ${env.GIT_COMMIT}"
            echo "git branch: ${env.BRANCH_NAME} ${env.GIT_BRANCH}"
            if (env.BRANCH_NAME != null && env.BRANCH_NAME.startsWith("Release")) {
                env.IS_RELEASE = "YES"
            }
            else {
                env.IS_RELEASE = "NO"
            }
        }
        
        bat """
            set BUILD_NUMBER=${env.BUILD_NUMBER}
            set GIT_COMMIT=${env.GIT_COMMIT}
            set GIT_BRANCH=${env.BRANCH_NAME}
            set RELEASE=${env.IS_RELEASE}
            cd package_builder
            build_python.bat install
            """
      }
    }
    
    stage("Trigger Downstream") {
      steps {
        build job: 'ibex_gui_pipeline', wait: false
      }
    }
  }
  
  post {
    failure {
      step([$class: 'Mailer', notifyEveryUnstableBuild: true, recipients: 'icp-buildserver@lists.isis.rl.ac.uk', sendToIndividuals: true])
    }
  }
  
  // The options directive is for configuration that applies to the whole job.
  options {
    buildDiscarder(logRotator(numToKeepStr:'5', daysToKeepStr: '7'))
    timeout(time: 60, unit: 'MINUTES')
    disableConcurrentBuilds()
  }
}
