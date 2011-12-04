import logging
from django.contrib.auth import logout as django_logout
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from sponge.utils import SpongeBundle, messages, set_rebalance_schedule, \
     config as config_utils
from sponge.utils.decorators import template, superuser_required
from sponge.forms.config import ConfigForm

__all__ = ["repos", "filters", "logout"]

logger = logging.getLogger(__name__)

def logout(request):
    bundle = SpongeBundle(request.user.username)
    bundle.delete()
    django_logout(request)
    url = reverse('django.contrib.auth.views.login') + "?next=/"
    return HttpResponseRedirect(url)

@superuser_required()
@template("config.html")
def configure(request):
    form = ConfigForm(request.POST or None)
    if request.POST:
        if form.is_valid():
            for name, value in form.cleaned_data.items():
                config_utils.set(name, value)
            messages.success(request, "Configuration options set")
            set_rebalance_schedule()
    return dict(form=form)
