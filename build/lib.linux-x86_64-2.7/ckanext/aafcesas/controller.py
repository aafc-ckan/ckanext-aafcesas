import logging

from ckan.common import config
from paste.deploy.converters import asbool
from six import text_type

import ckan.lib.base as base
import ckan.model as model
import ckan.lib.helpers as h
import ckan.authz as authz
import ckan.logic as logic
import ckan.logic.schema as schema
import ckan.lib.captcha as captcha
import ckan.lib.mailer as mailer
import ckan.lib.navl.dictization_functions as dictization_functions
import ckan.lib.authenticator as authenticator

import ckan.plugins as p
from ckan.common import _, c, request, response

from ckan.controllers.user import UserController

log = logging.getLogger(__name__)

abort = base.abort
render = base.render

check_access = logic.check_access
get_action = logic.get_action
NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
UsernamePasswordError = logic.UsernamePasswordError


class SimpleSSOUserController(UserController):
    """This controller is an example to show how you might extend or
    override core CKAN behaviour from an extension package.
    It overrides 2 method hooks which the base class uses to create the
    validation schema for the creation and editing of a user; to require
    that a fullname is given.
    """
    edit_user_form = 'user/edit_user_form.html'
    
    def __before__(self, action, **env):
        UserController.__before__(self, action, **env)
        try:
            context = {'model': model, 'user': c.user,
                       'auth_user_obj': c.userobj}
            check_access('site_read', context)
        except NotAuthorized:
            if c.action not in ('login', 'request_reset', 'perform_reset',):
                abort(403, _('Not authorized to see this page'))

    def edit(self, id=None, data=None, errors=None, error_summary=None):
        context = {'save': 'save' in request.params,
                   'schema': self._edit_form_to_db_schema(),
                   'model': model, 'session': model.Session,
                   'user': c.user, 'auth_user_obj': c.userobj
                   }
        if id is None:
            if c.userobj:
                id = c.userobj.id
            else:
                abort(400, _('No user specified'))
        data_dict = {'id': id}
        try:
            check_access('user_update', context, data_dict)
        except NotAuthorized:
            abort(403, _('Unauthorized to edit a user.'))
        if context['save'] and not data and request.method == 'POST':
            return self._save_edit(id, context)
        try:
            old_data = get_action('user_show')(context, data_dict)
            schema = self._db_to_edit_form_schema()
            if schema:
                old_data, errors = \
                    dictization_functions.validate(old_data, schema, context)
            c.display_name = old_data.get('display_name')
            c.user_name = old_data.get('name')
            data = data or old_data
        except NotAuthorized:
            abort(403, _('Unauthorized to edit user %s') % '')
        except NotFound:
            abort(404, _('User not found'))
        user_obj = context.get('user_obj')
        if not (authz.is_sysadmin(c.user)
                or c.user == user_obj.name):
            abort(403, _('User %s not authorized to edit %s') %
                  (str(c.user), id))
        errors = errors or {}
        vars = {'data': data, 'errors': errors, 'error_summary': error_summary}
        self._setup_template_variables({'model': model,
                                        'session': model.Session,
                                        'user': c.user},
                                       data_dict)
        c.is_myself = True
        c.show_email_notifications = asbool(
            config.get('ckan.activity_streams_email_notifications'))
        c.form = render(self.edit_user_form, extra_vars=vars)
        return render('user/edit.html')
