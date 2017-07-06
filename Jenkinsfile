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
        bat '''
            cd package_builder
            '''
      }
    }
	
	stage("Trigger Downstream") {
		build job: 'ibex_gui_pipeline'
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
