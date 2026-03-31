var appglobal = angular.module('appglobal', []);
appglobal.constant('mainapi', {
    'domain': 'https://www.bseindia.com/',
    'api_domain': 'https://api.bseindia.com/bseindia/api/',
    'other_domain': 'http://bws.bseindia.com/bseindia/api/',
    'bse_domain': 'https://www.bseindia.com/',

    'newapi_domain': 'https://api.bseindia.com/BseIndiaAPI/api/',
    'api_tesurl': 'https://testapiin.bseindia.com/BseIndiaAPI/api/',

    'api_domaintest': 'https://testapiin.bseindia.com/RealTimeBseIndiaAPI/api/',
    'api_domainRealTime': 'https://api.bseindia.com/RealTimeBseIndiaAPI/api/',
    'api_domainLIVE': 'https://api.bseindia.com/BseIndiaAPI/api/',

    'api_domainSearch': 'https://api.bseindia.com/'
});

appglobal.run(function ($rootScope, $templateCache) {
    $rootScope.$on('$viewContentLoaded', function () {
        $templateCache.removeAll();
    });
});
appglobal.filter("formatURL", function () {
    return function (x) {
        if (x != null && x != undefined)
            return x.toString().replace("http://www.bseindia.com", "").replace("https://www.bseindia.com", "").replace("www.bseindia.com", ""); else
            return x;
    }
}); appglobal.filter("aspxToHtml", function () {
    return function (x) {
        if (x != null && x != undefined)
            return x.toString().replace("/ann.aspx", "/ann.html"); else
            return x;
    }
});