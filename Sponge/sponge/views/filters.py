import logging
from sponge.utils import messages, filter as filter_utils
from sponge.utils.decorators import template
from sponge.forms import DeleteOkayForm
from sponge.forms.filter import FilterForm
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from pulp.client.api.filter import FilterAPI
from pulp.client.api.server import ServerRequestError

logger = logging.getLogger(__name__)

@template("filters.html")
def list(request):
    """ list filters """
    return dict(filters=filter_utils.list_filters().values())

@template("addfilter.html")
def add(request):
    if request.method == 'POST':
        form = FilterForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            filterapi = FilterAPI()
            try:
                filterapi.create(data['f_id'],
                                 data['f_type'],
                                 description=data['desc'],
                                 package_list=data['patterns'].splitlines())
                messages.success(request,
                                 "Created filter %s (%s)" %
                                 (data['desc'], data['f_id']))
                return \
                    HttpResponseRedirect(reverse('sponge.views.filters.list'))
            except ServerRequestError, err:
                messages.error(request,
                               "Failed to create filter %s (%s): %s" %
                               (data['desc'], data['f_id'], err[1]))
    return dict(form=FilterForm())

@template("viewfilter.html")
def view(request, filter_id=None):
    filterapi = FilterAPI()
    fltr = filter_utils.get_filter(filter_id)
    if request.method == 'POST':
        form = FilterForm(request.POST, filter=fltr)
        if form.is_valid():
            orig = [p
                    for p in form.cleaned_data['orig_patterns'].splitlines()
                    if p]
            new = [p for p in form.cleaned_data['patterns'].splitlines() if p]
            to_remove = [p for p in orig if p not in new]
            success = True
            if to_remove:
                try:
                    filterapi.remove_packages(filter_id, to_remove)
                    messages.success(request,
                                     "Removed patterns from filter %s: %s" %
                                     (fltr['description'],
                                      ", ".join(to_remove)))
                except ServerRequestError, err:
                    success = False
                    messages.error(request,
                                   "Failed to remove %d patterns (%s) from "
                                   "filter %s: %s" %
                                   (len(to_remove), ", ".join(to_remove),
                                    fltr['description'], err[1]))
            to_add = [p for p in new if p not in orig]
            if to_add:
                try:
                    filterapi.add_packages(filter_id, to_add)
                    messages.success(request,
                                     "Added patterns to filter %s: %s" %
                                     (fltr['description'],
                                      ", ".join(to_add)))
                except ServerRequestError, err:
                    success = False
                    messages.error(request,
                                   "Failed to add %d patterns (%s) to filter "
                                   "%s: %s" %
                                   (len(to_add), ", ".join(to_add),
                                    fltr['description'], err[1]))

            if success:
                return \
                    HttpResponseRedirect(reverse('sponge.views.filters.list'))

    return dict(filter=fltr,
                form=FilterForm(filter=fltr))


@template("deletefilter.html")
def delete(request, filter_id=None):
    filterapi = FilterAPI()
    fltr = filterapi.filter(filter_id)
    if request.method == 'POST':
        form = DeleteOkayForm(request.POST)
        if form.is_valid():
            try:
                filterapi.delete(filter_id, False)
                messages.success(request,
                                 "Deleted filter %s (%s)" %
                                 (fltr['description'], fltr['id']))
                return \
                    HttpResponseRedirect(reverse('sponge.views.filters.list'))
            except ServerRequestError, err:
                messages.error(request,
                               "Failed to delete filter %s (%s): %s"
                               (fltr['description'], fltr['id'], err[1]))
    return dict(filter=fltr,
                form=DeleteOkayForm(dict(id=filter_id)))
