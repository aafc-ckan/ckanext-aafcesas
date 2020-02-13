'''A CKAN plugin that enables SSO using a simple header parameter.

'''
import uuid
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import logging
from ckanext.aafcesas import controller
from ckan.common import  g, c
from ckan.plugins.toolkit import request, config
from flask import Blueprint
from ckanext.aafcesas.views import AafcESASEditView
import re
import unicodedata
from string import ascii_lowercase

dct={'0':'a','1':'b','2':'c','3':'d','4':'e',
     '5':'f','6':'g','7':'h','8':'i','9':'j'}

class AafcESASPlugin(plugins.SingletonPlugin):
    '''A CKAN plugin that enables SSO using a simple header parameter.

    '''
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IAuthenticator)
#    plugins.implements(plugins.IBlueprint)

    def update_config(self, config):
        '''Update CKAN config with settings needed by this plugin.

        '''
        plugins.toolkit.add_template_directory(config, 'templates')

    def login(self):
        pass

    def identify(self):
        '''Identify which user (if any) is logged in via simple SSO header.
        If a logged in user is found, set toolkit.c.user to be their user name.
        '''
        logger = logging.getLogger(__name__)
        shib_partyid= request.headers.get('partyId')
        logger.debug(request.headers)
        if not getattr(c, u'user', None):
            c.user = None
        if shib_partyid is None:
	    logger.debug("ESAS Identity not Found in HEADER")
        if shib_partyid is not None and c.user is None:
            logger.debug("ESAS Identity Found in Header")
            shib_email= request.headers.get('email')
            gives = text_to_id(request.headers.get('Legalgivennames'))
            fams = text_to_id(request.headers.get('Legalfamilyname'))
            nonumgives = re.sub('[0-9]+', '', gives)
            nonumfam = re.sub('[0-9]+', '', fams)
            shib_username= (alphabet_position(gives) + '_' + alphabet_position(fams)).lower()
            shib_fullname= nonumgives + ' ' + nonumfam
            logger.debug("partyId = \"{0}\"".format(shib_partyid)) 
            logger.debug("email = \"{0}\"".format(shib_email)) 
            logger.debug("username = \"{0}\"".format(shib_username)) 
            logger.debug("fullname = \"{0}\"".format(shib_fullname)) 
            check_user = get_user_by_userid(shib_partyid)
            # ESAS user is logged in and exists in CKAN
            if c.user and c.user==check_user['name']:
               logger.debug("User logged in already username = \"{0}\"".format(user['name'])) 
               # Check if ESAS email for user has changed.
               # If it has changed then update user email to match
               # CKAN is not system of record for email. 
               # Changes as needed to match ESAS header.
               current_email = get_email_by_userid(shib_partyid)
               if shib_email != current_email:
                   logger.info("ESAS: A user account has changed email.")
                   check_user=toolkit.get_action('user_update')(
                      context={'ignore_auth': True, 'user': 'ckan_admin'},
                      data_dict={'id':shib_partid,
                              'email': shib_email})
            elif c.user and c.user!=check_user['name']:
		   # User already logged in and ESAS header does not match
		   logger.info("ESAS: User already logged in to CKAN - \"{0}\"".format(c.user['name']))
		   logger.info("ESAS: Username in header - \"{0}\"".format(c.user['name']))
		   logger.info("ESAS: User being set to username in ESAS header.")

            elif check_user is not None and c.user is None:
		# User not logged in and ESAS header exists
		c.user = check_user['name']
            else:
                # A user with this username doesn't yet exist in CKAN
                # - so create one.
                logger.info("ESAS: user not found. Creating new CKAN user.")
                check_user = toolkit.get_action('user_create')(
                    context = {'ignore_auth': False, 'user': 'ckan_admin'},
                       data_dict={'email': shib_email,
                               'id': shib_partyid,
                               'name': shib_username,
                               'fullname': shib_fullname,
                               'password': generate_password()})
                logger.debug("username = \"{0}\"".format(check_user['name'])) 

    def logout(self):
        pass

    def abort(self, status_code, detail, headers, comment):
        pass

#    def get_blueprint(self):
#        blueprint = Blueprint('aafcesas',
#              self.__module__,
#              template_folder='templates')  
#        _edit_view = AafcESASEditView.as_view(str(u'edit'))
#        blueprint.add_url_rule(u'/user/edit',view_func=_edit_view)
#        blueprint.add_url_rule(u'/user/edit/<id>',view_func=_edit_view)
#        return blueprint

#def alter_user_edit_view(f):
#        def decorator(*args, **kwargs):
#             edit_user_form = u'/aafcesas/user/edit_user_form.html'
#             return f(*args, **kwargs)
#        return decorator
def strip_accents(text):
    """
    Strip accents from input String.

    :param text: The input string.
    :type text: String.

    :returns: The processed String.
    :rtype: String.
    """
    try:
        text = unicode(text, 'utf-8')
    except (TypeError, NameError): # unicode is a default on python 3 
        pass
    text = unicodedata.normalize('NFD', text)
    text = text.encode('ascii', 'ignore')
    text = text.decode("utf-8")
    return str(text)

def text_to_id(text):
    """
    Convert input text to id.

    :param text: The input string.
    :type text: String.

    :returns: The processed String.
    :rtype: String.
    """
    text = strip_accents(text.lower())
    text = re.sub('[ ]+', '_', text)
    text = re.sub('[^0-9a-zA-Z_-]', '', text)
    return text

def alphabet_position(text):
    text = text.lower()

    newstr=''
    for ch in text:
        if ch.isdigit()==True:
            dw=dct[ch]
            newstr=newstr+dw
        else:
            newstr=newstr+ch

    return ''.join(newstr)

def get_user_by_username(username):
        '''Return the CKAN user with the given username.
        :rtype: A CKAN user dict
        '''
        # We do this by accessing the CKAN model directly, because there isn't a
        # way to search for users by email address using the API yet.
        import ckan.model
        user = ckan.model.User.get(username)
        if user:
            user_dict = toolkit.get_action('user_show')(data_dict={'id': user.id})
            return user_dict
        else:
            return None

def get_user_by_userid(userid):
        '''Return the CKAN user with the given userid.
        :rtype: A CKAN user dict
        '''
        import ckan.model
        user = ckan.model.User.get(userid)
        if user:
            user_dict = toolkit.get_action('user_show')(data_dict={'id': user.id})
            return user_dict
        else:
            return None

def get_email_by_userid(userid):
        '''Return the CKAN user with the given userid.
        :rtype: A CKAN user dict
        '''
        import ckan.model
        user = ckan.model.User.get(userid)
        if user:
            user_email = user.email
            return user_email
        else:
            return None

def get_user_by_email(email):
        '''Return the CKAN user with the given email address.
        :rtype: A CKAN user dict
        '''
        # We do this by accessing the CKAN model directly, because there isn't a
        # way to search for users by email address using the API yet.
        import ckan.model
        users = ckan.model.User.by_email(email)
        assert len(users) in (0, 1), ("The AafcESAS plugin doesn't know what to do "
                                  "when CKAN has more than one user with the "
                                  "same email address.")
        if users:
            # But we need to actually return a user dict, so we need to convert it
            # here.
            user = users[0]
            user_dict = toolkit.get_action('user_show')(data_dict={'id': user.id})
            return user_dict
        else:
            return None

def generate_password():
        '''Generate a random password.
        '''
        # FIXME: Replace this with a better way of generating passwords, or enable
        # users without passwords in CKAN.
        return str(uuid.uuid4())
