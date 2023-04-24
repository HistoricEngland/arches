from django.core.cache import cache as core_cache
import pickle

DEFAULT_TTL = 120
CACHE_KEY_MAX_LENGTH = 250

def cache_key(request):
    """Generates a per user cache key based on the request object
    
    Args:
        request (object): django request object

    Returns:
        str: valid cache key
    """
    print(f"request: {request}")
    if request.user.is_anonymous:
        user = 'anonymous'
    else:
        user = request.user.id
    q = getattr(request, request.method)
    q.lists()
    urlencode = q.urlencode(safe='()')

    CACHE_KEY = 'req_cache_%s_%s_%s' % (request.path, user, urlencode)
    return CACHE_KEY

def get_cache_package(request, prefix, supported_verbs):
    """Generate a cache package for use in caching functions

    Args:
        request (object): The request object
        prefix (str): a key prefix to use. pass None if not needed
        supported_verbs (list => str): list of request verbs to support

    Returns:
        tuple: (CACHE_KEY, can_cache, response)
    """
    CACHE_KEY = cache_key(request)
    if prefix:
        CACHE_KEY = f"{prefix}_{CACHE_KEY}"
    
    can_cache = False
    if request.method in supported_verbs and len(CACHE_KEY) <= CACHE_KEY_MAX_LENGTH:
        can_cache = True
    if can_cache:
        response = core_cache.get(CACHE_KEY, None)
    else:
        response = None
        
    return (CACHE_KEY, can_cache, response)
            
def cache_per_user_view(ttl=DEFAULT_TTL, prefix=None, supported_verbs=['GET']):
    """Used as a decorator to cache the response of a view template get function.
    
    The function should have the parameters (self, request, *args, **kwargs).
    
    Args:
        ttl (_type_, optional): Duration to maintain cache in seconds. Defaults to DEFAULT_TTL.
        prefix (_type_, optional): Key Prefix if needed. Defaults to None.
        supported_verbs (list, optional): Request verbs to support. Defaults to ['GET'].
    """
    def decorator(function):
        def apply_cache(instance, request, *args, **kwargs):
            CACHE_KEY, can_cache, response = get_cache_package(request, prefix, supported_verbs)
            if not response:
                response = function(instance, request, *args, **kwargs)
                if can_cache:
                    core_cache.set(CACHE_KEY, response, ttl)
            return response
        return apply_cache
    return decorator

def cache_per_user_request(ttl=DEFAULT_TTL, prefix=None, supported_verbs=['GET']):
    """Used as a decorator to cache the response of a view function where a request object is passed in as the first argument.
    
    The function should have the parameters (request, *args, **kwargs).
    
    Args:
        ttl (_type_, optional): Duration to maintain cache in seconds. Defaults to DEFAULT_TTL.
        prefix (_type_, optional): Key Prefix if needed. Defaults to None.
        supported_verbs (list, optional): Request verbs to support. Defaults to ['GET'].
    """
    def decorator(function):
        def apply_cache(request, *args, **kwargs):
            CACHE_KEY, can_cache, response = get_cache_package(request, prefix, supported_verbs)
            if not response:
                response = function(request, *args, **kwargs)
                if can_cache:
                    core_cache.set(CACHE_KEY, response, ttl)
            return response
        return apply_cache
    return decorator

def cache_per_user_get_context(ttl=DEFAULT_TTL, prefix=None, supported_verbs=['GET']):
    def decorator(function):
        def apply_cache(instance, *args, **kwargs):
            request = instance.request
            CACHE_KEY, can_cache, response = get_cache_package(request, prefix, supported_verbs)
            if not response:
                response = function(instance, *args, **kwargs)
                if can_cache:
                    core_cache.set(CACHE_KEY, response, ttl)
            return response
        return apply_cache
    return decorator