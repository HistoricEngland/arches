from django.core.cache import cache as core_cache
import pickle

DEFAULT_TTL = 120

def cache_key(request):
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
    CACHE_KEY = cache_key(request)
    if prefix:
        CACHE_KEY = f"{prefix}_{CACHE_KEY}"
    
    can_cache = False
    if request.method in supported_verbs:
        can_cache = True
    if can_cache:
        response = core_cache.get(CACHE_KEY, None)
    else:
        response = None
        
    return (CACHE_KEY, can_cache, response)

def caching_per_user(request, value=None, ttl=DEFAULT_TTL, prefix=None, supported_verbs=['GET']):
    CACHE_KEY, can_cache, response = get_cache_package(request, prefix, supported_verbs)
    if not response:
        response = function(request)
        if can_cache:
            core_cache.set(CACHE_KEY, value, ttl)
    return response
            
def cache_per_user_view(ttl=DEFAULT_TTL, prefix=None, supported_verbs=['GET']):
    def decorator(function):
        def apply_cache(instance, request, *args, **kwargs):
            #CACHE_KEY = cache_key(request)
            #if prefix:
            #    CACHE_KEY = f"{prefix}_{CACHE_KEY}"
           
            #can_cache = False
            #if request.method in supported_verbs:
            #    can_cache = True
            #if can_cache:
            #    response = core_cache.get(CACHE_KEY, None)
            #else:
            #    response = None
            CACHE_KEY, can_cache, response = get_cache_package(request, prefix, supported_verbs)
            if not response:
                response = function(instance, request, *args, **kwargs)
                if can_cache:
                    core_cache.set(CACHE_KEY, response, ttl)
            return response
        return apply_cache
    return decorator

def cache_per_user_request(ttl=DEFAULT_TTL, prefix=None, supported_verbs=['GET']):
    def decorator(function):
        def apply_cache(request, *args, **kwargs):
            #CACHE_KEY = cache_key(request)
          
            #if prefix:
            #    CACHE_KEY = '%s_%s' % (prefix, CACHE_KEY)
          
            #can_cache = False
            #if request.method in supported_verbs:
            #    can_cache = True

            #if can_cache:
            #    response = core_cache.get(CACHE_KEY, None)
            #else:
            #    response = None
            
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
            #CACHE_KEY = cache_key(request)
          
            #if prefix:
            #    CACHE_KEY = '%s_%s' % (prefix, CACHE_KEY)
          
            #can_cache = False
            #if request.method in supported_verbs:
            #    can_cache = True

            #if can_cache:
            #    response = core_cache.get(CACHE_KEY, None)
            #else:
            #    response = None
            CACHE_KEY, can_cache, response = get_cache_package(request, prefix, supported_verbs)
            if not response:
                response = function(instance, *args, **kwargs)
                if can_cache:
                    core_cache.set(CACHE_KEY, response, ttl)
            return response
        return apply_cache
    return decorator