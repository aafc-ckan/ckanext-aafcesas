from flask import Blueprint
from ckan.views.user import EditView
import ckan.plugins as plugins
from ckan.common import _, config, g, request


class SimpleSSOEditView(EditView):
#    new_user_form = u'simplesso/user/new_user_form.html'
    edit_user_form = u'simplesso/user/edit_user_form.html'
