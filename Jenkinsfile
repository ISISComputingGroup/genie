#!groovy

pipeline {

  // agent defines where the pipeline will run.
  agent {  
    label "ndhspare53"
  }
  
  triggers {
    pollSCM('* * * * *')
  }
  
  stages {  
    stage("Checkout") {
      steps {
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
            echo "git branch: ${env.GIT_BRANCH}"
        }
        if (env.BRANCH_NAME.startsWith("Release")) {
            env.IS_RELEASE = "YES"
        }
        else {
            env.IS_RELEASE = "NO"
        }
        bat """
            set BUILD_NUMBER=${env.BUILD_NUMBER}
            set GIT_COMMIT=${env.GIT_COMMIT}
            set GIT_BRANCH=${env.GIT_BRANCH}
            set RELEASE=${env.IS_RELEASE}
            cd package_builder
            build_python.bat install
            """
      }
    }
    
    stage("Trigger Downstream") {
      steps {
        build job: 'ibex_gui_pipeline', wait: false
        build job: 'update_genie_python_vegas', wait: false
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
