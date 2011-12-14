import logging
from sponge.utils import messages
from sponge.utils.decorators import template
from sponge.forms import DeleteOkayForm
from sponge.models import CeleryTaskTracker
from sponge import tasks
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse

logger = logging.getLogger(__name__)

@template("tasks.html")
def list(request):
    tasktable = []
    tasklist = CeleryTaskTracker.objects.filter(owner=request.user.username)
    for task in tasklist:
        tclass = getattr(tasks, task.taskclass)
        tasktable.append(dict(id=task.taskid,
                              tclass=task.taskclass,
                              status=tclass.AsyncResult(task.taskid)))
    return dict(tasks=tasktable)

@template("deletetask.html")
def delete(request, task_id=None):
    taskapi = TaskAPI()
    task = CeleryTaskTracker.objects.filter(taskid=task_id)
    if request.method == 'POST':
        form = DeleteOkayForm(request.POST)
        if form.is_valid():
            tclass = getattr(tasks, task.taskclass)
            status = tclass.AsyncResult(task.taskid)
            task.delete()
            status.forget()
            messages.success(request,
                             "Deleted task %s (%s)" % (task.taskid,
                                                       task.taskclass))
            return HttpResponseRedirect(reverse('sponge.views.tasks.list'))
    return dict(task=task,
                form=DeleteOkayForm(dict(id=task_id)))
