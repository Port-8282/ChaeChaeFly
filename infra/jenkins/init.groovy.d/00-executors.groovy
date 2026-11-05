import jenkins.model.Jenkins

// Builds run on the registered Agent. Keep the controller for orchestration only.
def controller = Jenkins.get()
controller.setNumExecutors(0)
controller.save()
