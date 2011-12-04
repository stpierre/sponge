from sponge.utils import repo as repo_utils

register = template.Library()

def nevra(pkg):
    return repo_utils.get_nevra(pkg)

register.filter('nevra', nevra)
