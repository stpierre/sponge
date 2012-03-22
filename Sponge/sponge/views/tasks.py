import logging
from sponge.utils import messages, repo as repo_utils
from sponge.utils.decorators import template
from sponge.forms import DeleteOkayForm
from sponge.models import CeleryTaskTracker
from sponge import tasks
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from pulp.client.api.task import TaskAPI
from pulp.common.dateutils import parse_iso8601_datetime

logger = logging.getLogger(__name__)

@template("tasks.html")
def list(request):
    taskapi = TaskAPI()
    tasktable = []
    for task in CeleryTaskTracker.objects.filter(owner=request.user.username):
        tclass = getattr(tasks, task.taskclass)
        status = tclass.AsyncResult(task.taskid)
        stat_str = status.state
        if status.info:
            stat_str += ": %s" % status.info
        tasktable.append(dict(id=task.taskid,
                              command=task.taskclass,
                              status=stat_str,
                              repo=None,
                              type='sponge'))
    pulp_tasks = taskapi.list()
    if pulp_tasks:
        repos = repo_utils.get_repos()
        for task in taskapi.list():
            if task['start_time'] is not None and task['state'] != 'finished':
                status = task['state']
                command = task['method_name'].lstrip("_")
                if task['exception']:
                    status += ": " + task['exception']
                if task['scheduler'] == 'interval':
                    ttype = task['scheduler']
                    command = "Scheduled %s" % command
                else:
                    ttype = 'pulp'
                repo = None
                for arg in task['args']:
                    if arg in repos:
                        repo = arg
                        break
                tasktable.append(dict(id=task['id'],
                                      command=command,
                                      status=status,
                                      repo=repo,
                                      started=parse_iso8601_datetime(task['start_time']),
                                      type=ttype))
    return dict(tasks=tasktable)

@template("deletetask.html")
def delete(request, task_id=None):
    # figure out if this is a pulp task or a sponge task
    taskapi = TaskAPI()
    task = taskapi.info(task_id)
    if task is not None:
        command = task['method_name'].lstrip("_")
        if task['scheduler'] == 'interval':
            command = "Scheduled %s" % command
        
        if request.method == 'POST':
            form = DeleteOkayForm(request.POST)
            if form.is_valid():
                taskapi.cancel(task_id)
                messages.success(request,
                                 "Deleted task %s (%s)" % (task_id, command))
            return HttpResponseRedirect(reverse('sponge.views.tasks.list'))
        return dict(task_id=task_id,
                    command=command,
                    form=DeleteOkayForm(dict(id=task_id)))
    else:
        # must be a sponge task
        task = CeleryTaskTracker.objects.get(taskid=task_id)
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
        return dict(task_id=task.taskid,
                    command=task.taskclass,
                    form=DeleteOkayForm(dict(id=task_id)))
