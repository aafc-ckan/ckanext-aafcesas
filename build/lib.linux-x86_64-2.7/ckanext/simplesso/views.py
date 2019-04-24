import logging
from flask import Blueprint
from ckan.views.user import EditView
from paste.deploy.converters import asbool
from six import text_type

import ckan.plugins as plugins
from ckan.common import _, config, g, request
import ckan.logic as logic
from ckan import authz
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.model as model
import ckan.logic as logic
import ckan.logic.schema as schema

#new_user_form = u'/user/new_user_form.html'
edit_user_form = u'/user/edit_user_form.html'

def _get_repoze_handler(handler_name):
    u'''Returns the URL that repoze.who will respond to and perform a
    login or logout.'''
    return getattr(request.environ[u'repoze.who.plugins'][u'friendlyform'],
                   handler_name)

def _edit_form_to_db_schema():
    return schema.user_edit_form_schema()

def _new_form_to_db_schema():
    return schema.user_new_form_schema()

def _extra_template_variables(context, data_dict):
    is_sysadmin = authz.is_sysadmin(g.user)
    try:
        user_dict = logic.get_action(u'user_show')(context, data_dict)
    except logic.NotFound:
        h.flash_error(_(u'Not authorized to see this page'))
        return
    except logic.NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))
    is_myself = user_dict[u'name'] == g.user
    about_formatted = h.render_markdown(user_dict[u'about'])
    extra = {
        u'is_sysadmin': is_sysadmin,
        u'user_dict': user_dict,
        u'is_myself': is_myself,
        u'about_formatted': about_formatted
    }
    return extra

class SimpleSSOEditView(EditView):
    def get(self, id=None, data=None, errors=None, error_summary=None):
        context, id = self._prepare(id)
        data_dict = {u'id': id}
        try:
            old_data = logic.get_action(u'user_show')(context, data_dict)
            g.display_name = old_data.get(u'display_name')
            g.user_name = old_data.get(u'name')
            data = data or old_data
        except logic.NotAuthorized:
            base.abort(403, _(u'Unauthorized to edit user %s') % u'')
        except logic.NotFound:
            base.abort(404, _(u'User not found'))
        user_obj = context.get(u'user_obj')
        if not (authz.is_sysadmin(g.user) or g.user == user_obj.name):
            msg = _(u'User %s not authorized to edit %s') % (g.user, id)
            base.abort(403, msg)
        errors = errors or {}
        vars = {
            u'data': data,
            u'errors': errors,
            u'error_summary': error_summary
        }
        extra_vars = _extra_template_variables({
            u'model': model,
            u'session': model.Session,
            u'user': g.user
        }, data_dict)
        extra_vars[u'is_myself'] = True
        extra_vars[u'show_email_notifications'] = asbool(
            config.get(u'ckan.activity_streams_email_notifications'))
        vars.update(extra_vars)
        extra_vars[u'form'] = base.render(edit_user_form, extra_vars=vars)
        return base.render(u'user/edit.html', extra_vars)
