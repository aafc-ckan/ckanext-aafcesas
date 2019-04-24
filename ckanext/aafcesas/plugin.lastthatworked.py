'''A CKAN plugin that enables SSO using a simple header parameter.

'''
import uuid
import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import logging
from ckanext.simplesso import controller
from ckan.common import _, config, g, c, request

class SimpleSSOPlugin(plugins.SingletonPlugin):
    '''A CKAN plugin that enables SSO using a simple header parameter.

    '''
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IAuthenticator)

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
        shib_partyid= toolkit.request.headers.get('partyId')
        logger.debug(toolkit.request.headers)
        if shib_partyid is None:
	    logger.debug("ESAS Identity not Found in HEADER")
        if shib_partyid is not None:
            logger.debug("ESAS Identity Found in Header")
            shib_email= toolkit.request.headers.get('email')
            shib_username= (toolkit.request.headers.get('Legalgivennames') + '_' + toolkit.request.headers.get('Legalfamilyname')).lower()
            shib_fullname= toolkit.request.headers.get('Legalgivennames') + ' ' + toolkit.request.headers.get('Legalfamilyname')
            logger.debug("partyId = \"{0}\"".format(shib_partyid)) 
            logger.debug("email = \"{0}\"".format(shib_email)) 
            logger.debug("username = \"{0}\"".format(shib_username)) 
            logger.debug("fullname = \"{0}\"".format(shib_fullname)) 
            user = get_user_by_userid(shib_partyid)
            if user:
                logger.debug("User logged in already username = \"{0}\"".format(user['name'])) 
                # Check if ESAS email for user has changed.
                # If it has changed then update user email to match
                # CKAN is not system of record for email. 
                # Changes as needed to match ESAS header.
                current_email = get_email_by_userid(shib_partyid)
                if shib_email != current_email:
                    logger.info("ESAS: A user account has changed email.")
                    user=toolkit.get_action('user_update')(
                       context={'ignore_auth': True, 'user': 'ckan_admin'},
                       data_dict={'id':shib_partid,
                                  'email': shib_email})
            if not user:
                # Check if user email is already associated with an existing account.
                # If there are duplicate emails raise error
                # email_check = get_user_by_email(shib_email)
                # if email_check:
                #    logger.info("ESAS: An existing account already has this email")  
                # A user with this username doesn't yet exist in CKAN
                # - so create one.
                logger.info("ESAS: user not found. Creating new CKAN user.")
                user = toolkit.get_action('user_create')(
                    context = {'ignore_auth': True, 'user': 'ckan_admin'},
                    data_dict={'email': shib_email,
                               'id': shib_partyid,
                               'name': shib_username,
                               'fullname': shib_fullname,
                               'password': generate_password()})
                logger.debug("username = \"{0}\"".format(user['name'])) 
            c.user = user['name']

    def logout(self):
        pass

    def abort(self, status_code, detail, headers, comment):
        pass

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
        assert len(users) in (0, 1), ("The SimpleSSO plugin doesn't know what to do "
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
