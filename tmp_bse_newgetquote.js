
var getquote = angular.module('getquote', ["appglobal", "ngSanitize", "ngRoute"]);
getquote.constant('serviceurl', {
    url_sensexdata: 'GetSensexData/w',

    url_GetQuoteData: 'Msource/1D/getQouteSearch.aspx',
    url_CurrGetQuoteData: '/Source/getQuoteSearchBkPG.aspx',
    // Function to getquote header data.
    url_Compdata: 'ComHeadernew/w',
    //url_Leftmenu: 'LeftMenu/w',
    url_Leftmenu: 'LeftMenunew/w',
    url_Notiftn: 'Notification/w',
    url_ScripHeaderData: 'getScripHeaderData/w',
    url_StockTrading: 'StockTrading/w',
    url_PriceBand: 'PriceBand/w',
    url_Highlow: 'HighLow/w',
    url_Compname: 'CompanyName/w',
    url_Scripvalue: 'IrBackupData/W',
    url_ScripOHLC: 'ScriptHeader/w',
    url_ScripwiseCautionaryMsg: 'ScripwiseCautionaryMsg/w'
});


getquote.config(function ($routeProvider, $locationProvider) {
    $routeProvider
        //For Share holding
        .when('/stock-share-price/stockreach_shp.aspx?option:qstr', {
            templateUrl: '/GetQuote/stk_ShpQuarter.html',
            controller: 'shrhldController'
        })

        .when('/stock-share-price/stockreach_shp.aspx', {
            templateUrl: '/GetQuote/stk_ShpQuarter.html',
            controller: 'shrhldController'
        })
        .when('/stock-share-price/shp/scripcode/:scripcode/?option:qstr', {
            templateUrl: '/GetQuote/stk_ShpQuarter.html',
            controller: 'shrhldController'
        })
        .when('/stock-share-price/shp/scripcode/:scripcode/flag/:flag/', {
            templateUrl: '/GetQuote/stk_ShpQuarter.html',
            controller: 'shrhldController'
        })
        //for SDD shp development
        .when('/stock-share-price/shp/scripcode/:scripcode/sdd_flag/:flag/', {
            templateUrl: '/GetQuote/stk_sddshpquarter.html',
            controller: 'shrhldController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/flag/:flag/shp/', {
            templateUrl: '/GetQuote/stk_ShpQuarter.html',
            controller: 'shrhldController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/shp/', {
            templateUrl: '/GetQuote/stk_ShpQuarter.html',
            controller: 'shrhldController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/?option:qstr/shp/', {
            templateUrl: '/GetQuote/stk_ShpQuarter.html',
            controller: 'shrhldController'
        })

        //Share holding unit Pattern
        .when('/stock-share-price/shpunit/scripcode/:scripcode/flag/7/', {
            templateUrl: '/GetQuote/stk_unitholdinArch.html',
            controller: 'shrhldUnitController'
        })
        .when('/stock-share-price/shpunit/scripcode/:scripcode/', {
            templateUrl: '/GetQuote/stk_sharehold_Unit.html',
            controller: 'shrhldUnitController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/shpunit/', {
            templateUrl: '/GetQuote/stk_sharehold_Unit.html',
            controller: 'shrhldUnitController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/qtrid/:qtrid/shpunit/:qtrname/', {
            templateUrl: '/GetQuote/stk_sharehold_Unit.html',
            controller: 'shrhldUnitController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/qtrid/:qtrid/shpunit/', {
            templateUrl: '/GetQuote/stk_sharehold_Unit.html',
            controller: 'shrhldUnitController'
        })

        // Latest Share holding controller
        .when('/stock-share-price/shp-latest/scripcode/:scripcode/qtrid/:qtrid/', {
            templateUrl: '/GetQuote/stk_shpSecurities.html',
            controller: 'latestshrhldController'
        })
        .when('/stock-share-price/shp-latest/scripcode/:scripcode/', {
            templateUrl: '/GetQuote/stk_shpSecurities.html',
            controller: 'latestshrhldController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/qtrid/:qtrid/shareholding-pattern/:qtrname/', {
            templateUrl: '/GetQuote/stk_shpSecurities.html',
            controller: 'latestshrhldController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/qtrid/:qtrid/shareholding-pattern/', {
            templateUrl: '/GetQuote/stk_shpSecurities.html',
            controller: 'latestshrhldController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/shareholding-pattern/', {
            templateUrl: '/GetQuote/stk_shpSecurities.html',
            controller: 'latestshrhldController'
        })
        //for SDD SHP development
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/sddshareholding-pattern/', {
            templateUrl: '/GetQuote/stk_shpsecuritysdd.html',
            controller: 'sddshpController'
        })

        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/qtrid/:exchange_id/sddshareholding-pattern/:quarter/', {
            templateUrl: '/GetQuote/stk_sddshpquarter.html',
            controller: 'sddshpController'
        })

        //For reasearch reports
        .when('/stock-share-price/stockreach_reasearch_reports.aspx?option:qstr', {
            templateUrl: '/GetQuote/stk_research.html',
            controller: 'eqresearchController'
        })
        .when('/stock-share-price/stockreach_reasearch_reports.aspx', {
            templateUrl: '/GetQuote/stk_research.html',
            controller: 'eqresearchController'
        })
        .when('/stock-share-price/research-reports/scripcode/:scripcode/', {
            templateUrl: '/GetQuote/stk_research.html',
            controller: 'eqresearchController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/research-reports/', {
            templateUrl: '/GetQuote/stk_research.html',
            controller: 'eqresearchController'
        })
        //For consolidatepledge
        .when('/stock-share-price/stockreach_consolidatepledge.aspx?option:qstr', {
            templateUrl: '/GetQuote/stk_consolitedpledge.html',
            controller: 'eqconsolidatepledgeController'
        })
        .when('/stock-share-price/stockreach_consolidatepledge.aspx', {
            templateUrl: '/GetQuote/stk_consolitedpledge.html',
            controller: 'eqconsolidatepledgeController'
        })
        .when('/stock-share-price/disclosures/consolidated-pledge-data/:scripcode/', {
            templateUrl: '/GetQuote/stk_consolitedpledge.html',
            controller: 'eqconsolidatepledgeController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/disclosures-consolidated-pledge-data/', {
            templateUrl: '/GetQuote/stk_consolitedpledge.html',
            controller: 'eqconsolidatepledgeController'
        })
        //For sast 
        .when('/stock-share-price/stockreach_sast.aspx?option:qstr', {
            templateUrl: '/GetQuote/stk_sast.html',
            controller: 'eqsastController'
        })
        .when('/stock-share-price/stockreach_sast.aspx', {
            templateUrl: '/GetQuote/stk_sast.html',
            controller: 'eqsastController'
        })
        .when('/stock-share-price/disclosures/sast/:scripcode/', {
            templateUrl: '/GetQuote/stk_sast.html',
            controller: 'eqsastController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/disclosures-sast/', {
            templateUrl: '/GetQuote/stk_sast.html',
            controller: 'eqsastController'
        })
        //For Sast PIT
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/disclosures-sastpit/', {
            templateUrl: '/GetQuote/stk_sddPIT.html',
            controller: 'eqsddphase3_controller'
        })
        //For sast 31-4
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/disclosures-sast-31/', {
            templateUrl: '/GetQuote/stk_regthirtyone.html',
            controller: 'eqsast31Controller'
        })
        //For shareholders-meetings
        .when('/stock-share-price/stockreach_shareholdingmeeting.aspx?option:qstr', {
            templateUrl: '/GetQuote/stk_shareholdingmeeting.html',
            controller: 'eqshareholdingController'
        })
        .when('/stock-share-price/stockreach_shareholdingmeeting.aspx', {
            templateUrl: '/GetQuote/stk_shareholdingmeeting.html',
            controller: 'eqshareholdingController'
        })
        .when('/stock-share-price/meetings/shareholders-meetings/:scripcode/', {
            templateUrl: '/GetQuote/stk_shareholdingmeeting.html',
            controller: 'eqshareholdingController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/shareholders-meetings/', {
            templateUrl: '/GetQuote/stk_shareholdingmeeting.html',
            controller: 'eqshareholdingController'
        })
        //For voting-results
        .when('/stock-share-price/VotingResultMtingResult.aspx?option:qstr', {
            templateUrl: '/GetQuote/stk_votingresults.html',
            controller: 'eqvotingresultController'
        })
        .when('/stock-share-price/VotingResultMtingResult.aspx', {
            templateUrl: '/GetQuote/stk_votingresults.html',
            controller: 'eqvotingresultController'
        })
        .when('/stock-share-price/meetings/voting-results/:scripcode/', {
            templateUrl: '/GetQuote/stk_votingresults.html',
            controller: 'eqvotingresultController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/voting-results/', {
            templateUrl: '/GetQuote/stk_votingresults.html',
            controller: 'eqvotingresultController'
        })
        //For Debt meetings
        .when('/stock-share-price/meetings/Debt_meetingsDetails/:scripcode/', {
            templateUrl: '/GetQuote/stk_debtmeeting.html',
            controller: 'eqdebtmeetingresultController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/Debt_meetingsDetails/', {
            templateUrl: '/GetQuote/stk_debtmeeting.html',
            controller: 'eqdebtmeetingresultController'
        })
        //For insider-trading-1992
        .when('/stock-share-price/stockreach_insidertrade.aspx?option:qstr', {
            templateUrl: '/GetQuote/stk_insidertrade15.html',
            controller: 'eqinstrade15Controller'
        })
        .when('/stock-share-price/stockreach_insidertrade.aspx', {
            templateUrl: '/GetQuote/stk_insidertrade15.html',
            controller: 'eqinstrade15Controller'
        })
        .when('/stock-share-price/disclosures/insider-trading-1992/:scripcode/', {
            templateUrl: '/GetQuote/stk_insidertrade92.html',
            controller: 'eqinstrade92Controller'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/disclosures-insider-trading-1992/', {
            templateUrl: '/GetQuote/stk_insidertrade92.html',
            controller: 'eqinstrade92Controller'
        })
        //For insider-trading-2015 
        .when('/stock-share-price/stockreach_insidertrade_new.aspx?option:qstr', {
            templateUrl: '/GetQuote/stk_insidertrade15.html',
            controller: 'eqinstrade15Controller'
        })
        .when('/stock-share-price/stockreach_insidertrade_new.aspx', {
            templateUrl: '/GetQuote/stk_insidertrade15.html',
            controller: 'eqinstrade15Controller'
        })
        .when('/stock-share-price/disclosures/insider-trading-2015/:scripcode/', {
            templateUrl: '/GetQuote/stk_insidertrade15.html',
            controller: 'eqinstrade15Controller'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/disclosures-insider-trading-2015/', {
            templateUrl: '/GetQuote/stk_insidertrade15.html',
            controller: 'eqinstrade15Controller'
        })
        //For disclosures-sdd-sast-promoter
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/disclosures-sdd-sast-promoter/', {
            templateUrl: '/GetQuote/stk_sdd_sastpromoter.html',
            controller: 'eqsddsastprmtController'
        })
        //For disclosures-sdd-sast-non-promoter
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/disclosures-sdd-sast-non-promoter/', {
            templateUrl: '/GetQuote/stk_sdd_sastnonpromoter.html',
            controller: 'eqsddsastprmtController'
        })
        //For disclosures-sdd-sast-pledge
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/disclosures-sdd-sast-pledge/', {
            templateUrl: '/GetQuote/stk_sdd_sastpledge.html',
            controller: 'eqsddsastprmtController'
        })
        //For intermediaries DT 
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/disclosures-intermediariesDT/', {
            templateUrl: '/GetQuote/stk_intermedt.html',
            controller: 'disintermeDTCRA_controller'
            //controller: 'eqinstrade15Controller'
        })
        //For intermediaries CRA 
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/disclosures-intermediaries-CRA/', {
            templateUrl: '/GetQuote/stk_intermecra.html',
            controller: 'disintermeCRA_controller'
        })
        //For Rating action
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/disclosures-intermediaries-RatingAction/', {
            templateUrl: '/GetQuote/stk_intermRatingAction.html',
            controller: 'disinterRatingaction_controller'
        })
        //For  PIT Trading Plan
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/disclosures-PIT-Trading-Plan/', {

            templateUrl: '/GetQuote/stk_PIT_trading_plan.html',

            controller: 'PITTradingPlan_controller'
        })

        //For Intermediaries-ERP- shweta mhatre
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/intermediaries-ERP/', {

            templateUrl: '/GetQuote/stk_erp.html',

            controller: 'erpController'

        })
        //For peer-group-comparison
        .when('/stock-share-price/stockreach_peergroup.aspx?option:qstr', {
            templateUrl: '/GetQuote/stk_peergroup.html',
            controller: 'eqpeergroupController'
        })
        .when('/stock-share-price/stockreach_peergroup.aspx', {
            templateUrl: '/GetQuote/stk_peergroup.html',
            controller: 'eqpeergroupController'
        })
        .when('/stock-share-price/peer-group-comparison/scripcode/:scripcode/', {
            templateUrl: '/GetQuote/stk_peergroup.html',
            controller: 'eqpeergroupController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/peer-group-comparison/', {
            templateUrl: '/GetQuote/stk_peergroup.html',
            controller: 'eqpeergroupController'
        })
        ////For debt-other
        //.when('/stock-share-price/debt-other/scripcode/:scripcode/:seriescd/', {
        //    templateUrl: '/GetQuote/stkdebt.html',
        //    controller: 'eqdebtASController'
        //})
        //For corp-information
        .when('/stock-share-price/stockreach_corpinfo.aspx?option:qstr', {
            templateUrl: '/GetQuote/stk_corpinfo.html',
            controller: 'eqcorpinfoController'
        })
        .when('/stock-share-price/stockreach_corpinfo.aspx', {
            templateUrl: '/GetQuote/stk_corpinfo.html',
            controller: 'eqcorpinfoController'
        })
        .when('/stock-share-price/corp-information/scripcode/:scripcode/', {
            templateUrl: '/GetQuote/stk_corpinfo.html',
            controller: 'eqcorpinfoController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/corp-information/', {
            templateUrl: '/GetQuote/stk_corpinfo.html',
            controller: 'eqcorpinfoController'
        })
        //For corp-actions
        .when('/stock-share-price/stockreach_corpact.aspx?option:qstr', {
            templateUrl: '/GetQuote/stk_corpact.html',
            controller: 'eqcorpactController'
        })
        .when('/stock-share-price/stockreach_corpact.aspx', {
            templateUrl: '/GetQuote/stk_corpact.html',
            controller: 'eqcorpactController'
        })
        .when('/stock-share-price/corp-actions/scripcode/:scripcode/', {
            templateUrl: '/GetQuote/stk_corpact.html',
            controller: 'eqcorpactController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/corp-actions/', {
            templateUrl: '/GetQuote/stk_corpact.html',
            controller: 'eqcorpactController'
        })
        //For board-meetings
        .when('/stock-share-price/stockreach_boardmeeting.aspx?option:qstr', {
            templateUrl: '/GetQuote/stk_bordmeeting.html',
            controller: 'eqboardmeetingController'
        })
        .when('/stock-share-price/stockreach_boardmeeting.aspx', {
            templateUrl: '/GetQuote/stk_bordmeeting.html',
            controller: 'eqboardmeetingController'
        })
        .when('/stock-share-price/meetings/board-meetings/:scripcode/', {
            templateUrl: '/GetQuote/stk_bordmeeting.html',
            controller: 'eqboardmeetingController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/board-meetings/', {
            templateUrl: '/GetQuote/stk_bordmeeting.html',
            controller: 'eqboardmeetingController'
        })
        //For additional-info
        .when('/stock-share-price/additional-info/scripcode/:scripcode/', {
            templateUrl: '/GetQuote/stk_additionalinfo.html',
            controller: 'eqaddinfoController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/additional-info/', {
            templateUrl: '/GetQuote/stk_additionalinfo.html',
            controller: 'eqaddinfoController'
        })
        //For financials/annualreports
        .when('/stock-share-price/stockreach_annualreports.aspx?option:qstr', {
            templateUrl: '/GetQuote/stk_annualreport.html',
            controller: 'eqannreportController'
        })
        .when('/stock-share-price/stockreach_annualreports.aspx', {
            templateUrl: '/GetQuote/stk_annualreport.html',
            controller: 'eqannreportController'
        })
        .when('/stock-share-price/financials/annualreports/:scripcode/', {
            templateUrl: '/GetQuote/stk_annualreport.html',
            controller: 'eqannreportController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/financials-annual-reports/', {
            templateUrl: '/GetQuote/stk_annualreport.html',
            controller: 'eqannreportController'
        })
        //For financials/results
        .when('/stock-share-price/stockreach_financials.aspx?option:qstr', {
            templateUrl: '/GetQuote/stk_report.html',
            controller: 'eqreportController'
        })
        .when('/stock-share-price/stockreach_financials.aspx', {
            templateUrl: '/GetQuote/stk_report.html',
            controller: 'eqreportController'
        })
        .when('/stock-share-price/financials/results/:scripcode/', {
            templateUrl: '/GetQuote/stk_report.html',
            controller: 'eqreportController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/financials-results/', {
            templateUrl: '/GetQuote/stk_report.html',
            controller: 'eqreportController'
        })
        //for new result page format
        //.when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/financials-results_new/', {
        //    templateUrl: '/GetQuote/stk_financeresult.html',
        //    controller: 'eqreportController'
        //})
        //For financials/results/special
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/financials-results-special/', {
            templateUrl: '/GetQuote/stk_report_special.html',
            controller: 'eqreportspecialController'
        })
        //For bulk-block-deals
        .when('/stock-share-price/stockreach_bulkblock.aspx?option:qstr', {
            templateUrl: '/GetQuote/stk_blkblock.html',
            controller: 'eqbulkblockController'
        })
        .when('/stock-share-price/stockreach_bulkblock.aspx', {
            templateUrl: '/GetQuote/stk_blkblock.html',
            controller: 'eqbulkblockController'
        })
        .when('/stock-share-price/bulk-block-deals/scripcode/:scripcode/', {
            templateUrl: '/GetQuote/stk_blkblock.html',
            controller: 'eqbulkblockController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/bulk-block-deals/', {
            templateUrl: '/GetQuote/stk_blkblock.html',
            controller: 'eqbulkblockController'
        })
        //Corp Corpgovernane 
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/corporate-governance/', {
            templateUrl: '/GetQuote/stk_CorpgovernanceAnnexure.html',
            controller: 'CorpGovernanceController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/flag/:flag/corporate-governance/', {
            templateUrl: '/GetQuote/stk_CorpGovQuarter.html',
            controller: 'CorpGovernanceController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/:masterid/corporate-governance/:qtrname/', {
            templateUrl: '/GetQuote/stk_CorpgovernanceAnnexure.html',
            controller: 'CorpGovernanceController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/:masterid/corporate-governance/:qtrname/qtrid/:qtrid/', {
            templateUrl: '/GetQuote/stk_CorpgovernanceAnnexure.html',
            controller: 'CorpGovernanceController'
        })
        //for XBRL Integrated Filing (Governance) --shweta
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/integrated-filing-governance/', {
            templateUrl: '/GetQuote/stk_integratedfiling.html',
            controller: 'IntegratefileGovernanceController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/integrated-filing-finance/', {
            templateUrl: '/GetQuote/stk_integratedfinance.html',
            controller: 'IntegratefileGovernanceController'
        })
        //For Statement of Investor Complaints
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/qtrid/:qtrid/statement-of-investor-complaints/:qtrname/', {
            templateUrl: '/GetQuote/stk_investor_complaints.html',
            controller: 'eqinvestorcomplaintsController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/statement-of-investor-complaints/', {
            templateUrl: '/GetQuote/stk_investor_complaints.html',
            controller: 'eqinvestorcomplaintsController'
        })
        .when('/stock-share-price/sic/scripcode/:scripcode/flag/7/', {
            templateUrl: '/GetQuote/stk_sic.html',
            controller: 'eqsicController'
        })
        //For related-party-transactions
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/qtrid/:qtrid/related-party-transactions-new/:qtrname/', {
            templateUrl: '/GetQuote/stk_party_transactionsnew.html',
            controller: 'eqpartytransactionsController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/related-party-transactions-new/', {
            templateUrl: '/GetQuote/stk_party_transactionsnew.html',
            controller: 'eqpartytransactionsController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/qtrid/:qtrid/related-party-transactions/:qtrname/', {
            templateUrl: '/GetQuote/stk_party_transactions.html',
            controller: 'eqpartytransactionsController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/related-party-transactions/', {
            templateUrl: '/GetQuote/stk_party_transactions.html',
            controller: 'eqpartytransactionsController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/flag/7/rpt/', {
            templateUrl: '/GetQuote/stk_prt.html',
            controller: 'eqprtController'

        })
        .when('/stock-share-price/rpt/scripcode/:scripcode/flag/7/', {
            templateUrl: '/GetQuote/stk_prt.html',
            controller: 'eqprtController'

        })
        //For BRSR
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/brsr/', {
            templateUrl: '/GetQuote/stk_brsr.html',
            controller: 'eqbrsrController'
        })
        //For ASCR
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/ascr/', {
            templateUrl: '/GetQuote/stk_ascr.html',
            controller: 'eqascrController'
        })
        //For UPSI
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/upsi/', {
            templateUrl: '/GetQuote/stk_upsi.html',
            controller: 'eqmfupsiController'
        })
        //For Off market transaction
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/Off-market-transaction/', {
            templateUrl: '/GetQuote/stk_mfmkttrans.html',
            controller: 'eqmfupsiController'
        })
        //For Trading Plan
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/trading-plan/', {
            templateUrl: '/GetQuote/stk_mftrdplan.html',
            controller: 'eqmfupsiController'
        })
        //For Quarterly Disclosures
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/quarterly-disclosures/', {
            templateUrl: '/GetQuote/stk_mfqtrdis.html',
            controller: 'eqmfupsiController'
        })
        //For Event Based Disclosures
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/event-based-disclosures/', {
            templateUrl: '/GetQuote/stk_mfeventbase.html',
            controller: 'eqmfupsiController'
        })
        //For MF PIT Corp Information
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/pit-corp-information/', {
            templateUrl: '/GetQuote/stk_mfcorpinfo.html',
            controller: 'eqmfupsiController'
        })
        //Corp Announcements Controller
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/corp-announcements/', {
            templateUrl: '/GetQuote/stk_Ann.html',
            controller: 'corpannController'
        })
        .when('/stock-share-price/:scripfullname/:scripshortname/:scripcode/', {
            templateUrl: '/GetQuote/stk_equity.html',
            controller: 'equityController'
        })
        .when('/stock-share-price/debt-other/scripcode/:scripcode/:seriescd/', {
            redirectTo: '/GetQuote/stkdebt.html'
        })
        .when('/index.html', {
            redirectTo: '/index.html'
        })
        .when('/about.html', {
            redirectTo: '/about.html'
        })
        .when('/investor_relation.html', {
            redirectTo: '/investor_relation.html'
        })
        .when('/markets.html', {
            redirectTo: '/markets.html'
        })
        .when('/publicissue.html', {
            redirectTo: '/publicissue.html'
        })
        .when('/corporates.html', {
            redirectTo: '/corporates.html'
        })
        .when('/members.html', {
            redirectTo: '/members.html'
        })
        .when('/investor.html', {
            redirectTo: '/investor.html'
        })
        .when('/market_data_products.html?option:qstr', {
            redirectTo: '/market_data_products.html?flag=real'
        })
        .when('/market_data_products.html', {
            redirectTo: '/market_data_products.html'
        })
        .when('http://www.bsebti.com/', {
            redirectTo: 'http://www.bsebti.com/'
        })
        .otherwise({
            redirectTo: 'stock-share-price'
        });
    $locationProvider.html5Mode(true);
});

// Header Controller
getquote.controller('headerController', ['serviceurl', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$routeParams', '$window', function headerController(serviceurl, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $routeParams, $window) {

    var seriescd = 0;
    var scripcode;
    var type;
    var Fname;
    var Sname;
    var querystr = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
    $scope.getUrlParameter = function (param, dummyPath) {
        var sPageURL = dummyPath || window.location.search.substring(1),
            sURLVariables = sPageURL.split(/[&||?]/),
            res;
        for (var i = 0; i < sURLVariables.length; i += 1) {
            var paramName = sURLVariables[i],
                sParameterName = (paramName || '').split('=');
            if (sParameterName[0] === param) {
                res = sParameterName[1];
            }
        }
        return res;
    };
    if (querystr.indexOf('=') == -1) {
        var a = querystr.split('/')
        scripcode = a[6];
        type = a[5];
        Fname = a[4];
        Sname = a[5];
    }
    else {
        scripcode = $scope.getUrlParameter('scripcode', querystr);
    }

    $rootScope.camelize = function (str) {
        if ((str === null) || (str === ''))
            return false;
        else
            str = str.toString();

        return str.replace(/\w\S*/g, function (txt) { return txt.charAt(0).toUpperCase() + txt.substr(1).toLowerCase(); });
    }



    var pop = 0;
    var pathname;
    window.onpopstate = function (event) {

        if (document.location.pathname === '/' && pop > 1) {
            pop = 0;
            history.pushState("", document.title, window.location.pathname);
            location.reload();
        }
        pop++;
        window.location = window.location.pathname
    }


    $scope.scripcode = scripcode;
    var inputtext;
    var ddltype;
    var url;
    var sinx = localStorage.getItem('QuoteIntex');
    if (typeof sinx !== "undefined" && sinx !== null && sinx !== "") {
        $scope.selectedseg = sinx;
    }
    else { $scope.selectedseg = 'EQ'; }

    $scope.loader = {
        toploading: 'loading',
        sloading: false,
        sloaded: false,
        CAloading: false,
        CAloaded: false,
        Cloading: false,
        Cloaded: false,
        NTloading: false,
        NTloaded: false,
        LFloading: false,
        LFloaded: false,
        STdelay: false,
        PBdelay: false,
        PBState: 'loading',
        STState: 'loading',
        HLState: 'loading',
        HLdelay: false,
    };

    $rootScope.SensexTable = function () {
        $scope.loader.sloading = true;
        $scope.loader.sloaded = false;
        $scope.loader.toploading = 'loading';
        // var url = $injector.get('api_domain') + $injector.get('url_sensexdata');
        var url = mainapi.api_domainRealTime + serviceurl.url_sensexdata;
        $http.get(url).then(function successCallback(response) {
            //$scope.HeaderData = response.data;
            $rootScope.HeaderData = response.data;
            $scope.loader.sloading = false;
            $scope.loader.sloaded = true;
            $scope.loader.toploading = 'loaded';
            $scope.$emit('childdata', { msg: $rootScope.HeaderData });
        }, function errorCallback(response) {
            $scope.loader.toploading = 'loading';
            $scope.status = response.status + "_" + response.statusText;
        });
    };
    $scope.GetQuoteTable = function (event) {
        if (event.keyCode != 40 && event.keyCode != 38 && event.keyCode != 13) {
            ddltype = $('#ddltype option:selected').val();
            inputtext = $('#getquotesearch').val();

            if (inputtext != "" && inputtext.length > 1) {
                //var url = $injector.get('domain') + $injector.get('url_GetQuoteData')+'?Type=' + ddltype + '&text=' + inputtext;
                //var url = '/Source/GetQuoteData.aspx?Type=' + ddltype + '&text=' + inputtext;
                if (ddltype == "CR") {
                    url = serviceurl.url_CurrGetQuoteData + '?Type=' + ddltype + '&text=' + inputtext;
                }
                else if (ddltype == "CO") {
                    url = serviceurl.url_CurrGetQuoteData + '?Type=' + ddltype + '&text=' + inputtext;
                }
                else if (ddltype == "EGR") {
                    url = serviceurl.url_CurrGetQuoteData + '?Type=' + ddltype + '&text=' + inputtext
                }
                else {
                    url = mainapi.api_domainSearch + serviceurl.url_GetQuoteData + '?Type=' + ddltype + '&text=' + inputtext + "&flag=site";
                    // url = $injector.get('url_GetQuoteData') + '?Type=' + ddltype + '&text=' + inputtext + "&flag=nw";
                }

                $http.get(url).then(function successCallback(response) {
                    $scope.SearchQuote = response.data;
                    $('#ulSearchQuote').css({ "display": "block" });

                }, function errorCallback(response) {
                    $scope.status = response.status + "_" + response.statusText;
                });
            }
            else {
                $scope.SearchQuote = "";
                $('#ulSearchQuote').css({ "display": "none" });
            }
        }
    }
    $scope.ClearList = function () {
        localStorage.setItem('QuoteIntex', $('#ddltype option:selected').val());
        $scope.SearchQuote = "";
        $('#ulSearchQuote').css({ "display": "none" });
        var selectedValue = $('#ddltype option:selected').val();
        $('#getquotesearch').val('');
    }

    if ($scope.scripcode == null || $scope.scripcode == undefined) {
        $scope.scripcode = 000;//500325;//501479;//503772;
    }
    $scope.fn_getgoute = function (querystr) {
        $scope.loader = {
            toploading: 'loading',
            sloading: false,
            sloaded: false,
            CAloading: false,
            CAloaded: false,
            Cloading: false,
            Cloaded: false,
            NTloading: false,
            NTloaded: false,
            LFloading: false,
            LFloaded: false,
            STdelay: false,
            PBdelay: false,
            PBState: 'loading',
            STState: 'loading',
            HLState: 'loading',
            HLdelay: false,
        };
        var scripcode;
        var type;
        querystr.replace(/[\\#,+()$~%.":*<>{};]/g, '_');
        $scope.getUrlParameter = function (param, dummyPath) {
            var sPageURL = dummyPath || window.location.search.substring(1),
                sURLVariables = sPageURL.split(/[&||?]/),
                res;
            for (var i = 0; i < sURLVariables.length; i += 1) {
                var paramName = sURLVariables[i],
                    sParameterName = (paramName || '').split('=');
                if (sParameterName[0] === param) {
                    res = sParameterName[1];
                }
            }
            return res;
        };
        if (querystr.indexOf('=') == -1) {
            var a = querystr.split('/')
            scripcode = a[4];
            type = a[3];
        }
        else {
            scripcode = $scope.getUrlParameter('scripcode', querystr);
        }
        $scope.scripcode = scripcode;
    }
    $scope.Intervalflag = 0;
    $scope.fn_ScripHeaderData = function () {

        $scope.count = 0;
        $scope.loader.Cloading = true;
        $scope.loader.Cloaded = false;
        var url = mainapi.newapi_domain + serviceurl.url_ScripHeaderData;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, seriesid: "", Debtflag: "" } }).then(function successCallback(response) {
            $scope.ScripHeaderData = response.data;

            if ($scope.ScripHeaderData != undefined) {
                $scope.ScripHeaderData.Header.divremarks = "";
                if ($scope.ScripHeaderData.Header.Invit == "1") {
                    $scope.count = $scope.count + 1;
                    //$("#divremarks").html("<span style='font-size:12px;text-align:left;color: black;'>Face value is the issue price determined in the IPO, as face value is not applicable for units of an InvIT</span>");
                    $scope.ScripHeaderData.Header.divremarks = $scope.ScripHeaderData.Header.divremarks + "<span style='font-size:12px;text-align:left;color: black;'>Face Value is Not Applicable for Units of InvITs/REITs</span>";
                }


                if ($scope.ScripHeaderData.Header.IsALF != undefined && $scope.ScripHeaderData.Header.IsALF != "" && $scope.ScripHeaderData.Header.IsALF == "1" && $scope.count > 0) {
                    $scope.count = $scope.count + 1;
                    $scope.ScripHeaderData.Header.divremarks = $scope.ScripHeaderData.Header.divremarks + "<span class='sensexredtext'> |<a href='/static/about/nonpaymentlistingfee.aspx'Target='_blank' style='color: red;'> Company has not paid Annual Listing Fees and is in violation of SEBI & Exchange Regulations.</span>";
                }
                else if ($scope.ScripHeaderData.Header.IsALF != undefined && $scope.ScripHeaderData.Header.IsALF != "" && $scope.ScripHeaderData.Header.IsALF == "1" && $scope.count == 0) {
                    $scope.count = $scope.count + 1;
                    $scope.ScripHeaderData.Header.divremarks = $scope.ScripHeaderData.Header.divremarks + "<span class='sensexredtext'><a href='/static/about/nonpaymentlistingfee.aspx' Target='_blank' style='color: red;' >Company has not paid Annual Listing Fees and is in violation of SEBI & Exchange Regulations.</span>";
                }

                if ($scope.ScripHeaderData.Header.GSMText != undefined && $scope.ScripHeaderData.Header.GSMText != "" && $scope.count > 0) {
                    $scope.count = $scope.count + 1;
                    //$("#divremarks").html("<p><span style='font-size:12px;text-align:right;color:black;'>Face value is the issue price determined in the IPO, as face value is not applicable for units of an InvIT</span><span><a href='" + $scope.ScripOHLC.GSMURL + "' Target='_blank' style='color: red;'>" + $scope.ScripOHLC.GSMText + "</a><span></p>");
                    $scope.ScripHeaderData.Header.divremarks = $scope.ScripHeaderData.Header.divremarks + "<span> | <a href='" + $scope.ScripHeaderData.Header.GSMURL + "' Target='_blank' style='color: red;'>" + $scope.ScripHeaderData.Header.GSMText + "</a><span>";
                }
                else if ($scope.ScripHeaderData.Header.GSMText != undefined && $scope.ScripHeaderData.Header.GSMText != "" && $scope.count == 0) {
                    $scope.count = $scope.count + 1;
                    //$("#divremarks").html("<p style='font-size:12px;color:#de1439;text-align:right;'><a href='" + $scope.ScripOHLC.GSMURL + "' Target='_blank' style='color: red;'>" + $scope.ScripOHLC.GSMText + "</a></p>");
                    $scope.ScripHeaderData.Header.divremarks = $scope.ScripHeaderData.Header.divremarks + "<span><a class='sensexredtext' href='" + $scope.ScripHeaderData.Header.GSMURL + "' Target='_blank'>" + $scope.ScripHeaderData.Header.GSMText + "</a></span>";
                }

                if ($scope.ScripHeaderData.Header.ASMText != undefined && $scope.ScripHeaderData.Header.ASMText != "" && $scope.count > 0) {

                    $scope.count = $scope.count + 1;
                    $scope.ScripHeaderData.Header.divremarks = $scope.ScripHeaderData.Header.divremarks + "<span> | <a class='sensexredtext' href='" + $scope.ScripHeaderData.Header.ASMURL + "' Target='_blank'>" + $scope.ScripHeaderData.Header.ASMText + "</a></span>";
                }
                else if ($scope.ScripHeaderData.Header.ASMText != undefined && $scope.ScripHeaderData.Header.ASMText != "" && $scope.count == 0) {
                    $scope.count = $scope.count + 1;
                    $scope.ScripHeaderData.Header.divremarks = $scope.ScripHeaderData.Header.divremarks + "<span><a class='sensexredtext' href='" + $scope.ScripHeaderData.Header.ASMURL + "' Target='_blank'>" + $scope.ScripHeaderData.Header.ASMText + "</a></span>";
                }

                if ($scope.ScripHeaderData.Header.SMSText != undefined && $scope.ScripHeaderData.Header.SMSText != "" && $scope.count > 0) {
                    $scope.count = $scope.count + 1;
                    $scope.ScripHeaderData.Header.divremarks = $scope.ScripHeaderData.Header.divremarks + " <span> | <a class='sensexredtext' href='" + $scope.ScripHeaderData.Header.SMSURL + "' Target='_blank'>" + $scope.ScripHeaderData.Header.SMSText + "</a></span>";
                }
                else if ($scope.ScripHeaderData.Header.SMSText != undefined && $scope.ScripHeaderData.Header.SMSText != "" && $scope.count == 0) {
                    $scope.count = $scope.count + 1;
                    $scope.ScripHeaderData.Header.divremarks = $scope.ScripHeaderData.Header.divremarks + "<span><a class='sensexredtext' href='" + $scope.ScripHeaderData.Header.SMSURL + "' Target='_blank'>" + $scope.ScripHeaderData.Header.SMSText + "</a></span>";
                }

                if ($scope.ScripHeaderData.Header.IRPText != undefined && $scope.ScripHeaderData.Header.IRPText != "" && $scope.count > 0) {
                    $scope.count = $scope.count + 1;
                    $scope.ScripHeaderData.Header.divremarks = $scope.ScripHeaderData.Header.divremarks + " <span> | <a class='sensexredtext' href='" + $scope.ScripHeaderData.Header.IRPURL + "' Target='_blank'>" + $scope.ScripHeaderData.Header.IRPText + "</a></span>";
                }
                else if ($scope.ScripHeaderData.Header.IRPText != undefined && $scope.ScripHeaderData.Header.IRPText != "" && $scope.count == 0) {
                    $scope.count = $scope.count + 1;
                    $scope.ScripHeaderData.Header.divremarks = $scope.ScripHeaderData.Header.divremarks + "<span><a class='sensexredtext' href='" + $scope.ScripHeaderData.Header.IRPURL + "' Target='_blank'>" + $scope.ScripHeaderData.Header.IRPText + "</a></span>";
                }
                if ($scope.ScripHeaderData.Header.EMSText != undefined && $scope.ScripHeaderData.Header.EMSText != "" && $scope.count > 0) {
                    $scope.count = $scope.count + 1;
                    $scope.ScripHeaderData.Header.divremarks = $scope.ScripHeaderData.Header.divremarks + " <span> | <a class='sensexredtext' href='" + $scope.ScripHeaderData.Header.EMSURL + "' Target='_blank'>" + $scope.ScripHeaderData.Header.EMSText + "</a></span>";
                }
                else if ($scope.ScripHeaderData.Header.EMSText != undefined && $scope.ScripHeaderData.Header.EMSText != "" && $scope.count == 0) {
                    $scope.count = $scope.count + 1;
                    $scope.ScripHeaderData.Header.divremarks = $scope.ScripHeaderData.Header.divremarks + "<span><a class='sensexredtext' href='" + $scope.ScripHeaderData.Header.EMSURL + "' Target='_blank'>" + $scope.ScripHeaderData.Header.EMSText + "</a></span>";
                }
                if ($scope.ScripHeaderData.CompResp.compRes != undefined && $scope.ScripHeaderData.CompResp.compRes != "" && $scope.count > 0) {
                    $scope.count = $scope.count + 1;
                    $scope.ScripHeaderData.Header.divremarks = $scope.ScripHeaderData.Header.divremarks + " <span> | <a class='sensexredtext' href='" + $scope.ScripHeaderData.CompResp.texturl + "' Target='_blank'>" + $scope.ScripHeaderData.CompResp.compRes + "</a></span>";
                }
                else if ($scope.ScripHeaderData.CompResp.compRes != undefined && $scope.ScripHeaderData.CompResp.compRes != "" && $scope.count == 0) {
                    $scope.count = $scope.count + 1;
                    $scope.ScripHeaderData.Header.divremarks = $scope.ScripHeaderData.Header.divremarks + "<span><a class='sensexredtext' href='" + $scope.ScripHeaderData.CompResp.texturl + "' Target='_blank'>" + $scope.ScripHeaderData.CompResp.compRes + "</a></span>";
                }
                if ($scope.count > 0) {
                    $scope.ScripHeaderData.Header.divremarks = "<p>" + $scope.ScripHeaderData.Header.divremarks + "</p>";
                }
            }

            $scope.$emit('DayOHLC', { High: $scope.ScripHeaderData.Header.High, Low: $scope.ScripHeaderData.Header.Low, LTP: $scope.ScripHeaderData.Header.LTP });

            if ($scope.Intervalflag == 0) {
                $('html, body').animate({
                    scrollTop: $("#equity1").offset().top
                }, 0);
            }
        },
            function errorCallback(response) {
                $scope.status = response.status + "_" + response.statusText;
            });
    }
    $scope.fnCompanyname = function () {
        $scope.loader.Cloading = true;
        $scope.loader.Cloaded = false;
        var url = mainapi.api_domainLIVE + serviceurl.url_Compname;
        //$http.post(url, '{"scripcode":"' + $scope.scripcode + '","seriesid":""}').then(function successCallback(response) {
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, seriesid: "" } }).then(function successCallback(response) {
            $scope.CompName = response.data;
            $scope.loader.Cloading = false;
            $scope.loader.Cloaded = true;
            $scope.loader.Cdelay = false;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.Cdelay = true;
            }
        });
    }
    $scope.fnScripvalue = function () {
        var url = mainapi.api_domainLIVE + serviceurl.url_Scripvalue;
        // $http.post(url, '{"scripcode":"' + $scope.scripcode + '","DebtFlag":"C"}').then(function successCallback(response) {
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, DebtFlag: "C" } }).then(function successCallback(response) {
            $scope.ScripValue = response.data;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
        });
    }
    $scope.fnScripOHLC = function () {
        $scope.loader.Cloading = true;
        $scope.loader.Cloaded = false;
        var url = mainapi.api_domainLIVE + serviceurl.url_ScripOHLC;
        // $http.post(url, '{"scripcode":"' + $scope.scripcode + '","seriesid":""}').then(function successCallback(response) {
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, seriesid: "" } }).then(function successCallback(response) {
            $scope.ScripOHLC = response.data;
            $scope.loader.Cloading = false;
            $scope.loader.Cloaded = true;
            $scope.loader.CHdelay = false;
            if ($scope.ScripOHLC != undefined) {
                if ($scope.ScripOHLC.GSMText != undefined && $scope.ScripOHLC.GSMText != "" && $scope.ScripOHLC.Invit == "1") {
                    //$("#divremarks").html("<p><span style='font-size:12px;text-align:right;color:black;'>Face value is the issue price determined in the IPO, as face value is not applicable for units of an InvIT</span><span><a href='" + $scope.ScripOHLC.GSMURL + "' Target='_blank' style='color: red;'>" + $scope.ScripOHLC.GSMText + "</a><span></p>");
                    $scope.ScripOHLC.divremarks = "<p><span style='font-size:12px;text-align:right;color:black;'>Face Value is Not Applicable for Units of InvITs/REITs</span><span><a href='" + $scope.ScripOHLC.GSMURL + "' Target='_blank' style='color: red;'>" + $scope.ScripOHLC.GSMText + "</a><span></p>";
                }
                else if ($scope.ScripOHLC.GSMURL != undefined && $scope.ScripOHLC.GSMURL != "") {
                    //$("#divremarks").html("<p style='font-size:12px;color:#de1439;text-align:right;'><a href='" + $scope.ScripOHLC.GSMURL + "' Target='_blank' style='color: red;'>" + $scope.ScripOHLC.GSMText + "</a></p>");
                    $scope.ScripOHLC.divremarks = "<p><a href='" + $scope.ScripOHLC.GSMURL + "' Target='_blank'>" + $scope.ScripOHLC.GSMText + "</a></p>";
                }
                else if ($scope.ScripOHLC.Invit == "1") {
                    //$("#divremarks").html("<span style='font-size:12px;text-align:left;color: black;'>Face value is the issue price determined in the IPO, as face value is not applicable for units of an InvIT</span>");
                    $scope.ScripOHLC.divremarks = "<span style='font-size:12px;text-align:left;color: black;'>Face Value is Not Applicable for Units of InvITs/REITs</span>";
                }
                $scope.$emit('DayOHLC', { High: $scope.ScripOHLC.High, Low: $scope.ScripOHLC.Low, LTP: $scope.ScripOHLC.LTP });
            }
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.CHdelay = true;
            }
        });
    }

    $scope.fnCompanydata = function () {
        $scope.loader.CDloading = true;
        $scope.loader.CDloaded = false;
        var url = mainapi.newapi_domain + serviceurl.url_Compdata;
        //$http.post(url, '{"scripcode":"' + $scope.scripcode + '","quotetype":"EQ","seriesid":""}').then(function successCallback(response) {
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, quotetype: "EQ", seriesid: "" } }).then(function successCallback(response) {
            $scope.CompData = response.data;
            $scope.loader.CDloading = false;
            $scope.loader.CDloaded = true;
            $scope.loader.CDdelay = false;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;

            if (response.status == (500 || 503)) {
                $scope.loader.CDdelay = true;
            }
        });
    }

    $scope.fnNotiftn = function () {
        $scope.loader.NTloading = true;
        $scope.loader.NTloaded = false;
        var url = mainapi.api_domainLIVE + serviceurl.url_Notiftn;
        //$http.post(url, '{"scripcode":"' + $scope.scripcode + '"}').then(function successCallback(response) {
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode } }).then(function successCallback(response) {
            $scope.Notiftn = response.data;
            $scope.loader.NTloading = false;
            $scope.loader.NTloaded = true;
            $scope.loader.NTdelay = false;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.NTdelay = true;
            }
        });
    }
    $rootScope.pagedebt = false;
    $rootScope.Dclassbname = "";
    $rootScope.Eclassbname = "dropdown mega-dropdown landingsec";
    $rootScope.DBclassbname = "";
    $rootScope.Sclassbname = "";
    $rootScope.isequity = true;
    $scope.fnLeftmenu = function () {
        $rootScope.DBclassbname = "";
        $rootScope.Eclassbname = "dropdown mega-dropdown landingsec";
        $scope.loader.LFloading = true;
        $scope.loader.LFloaded = false;
        var url = mainapi.api_domainLIVE + serviceurl.url_Leftmenu;
        //$http.post(url, '{"scripcode":"' + $scope.scripcode + '","quotetype":"LMN"}').then(function successCallback(response) {
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, quotetype: "LMN" } }).then(function successCallback(response) {
            $scope.Leftmenudata = response.data;
            if ($scope.scripcode >= 700000 && $scope.scripcode <= 999999) {
                $rootScope.pagedebt = true;
                $rootScope.isequity = false;
            }
            else if ($scope.Leftmenudata.showDEBT && $scope.Leftmenudata.showETF == false) { $scope.pagedebt = true; }

            $rootScope.SEOURL = $scope.Leftmenudata.EQSEOurl;
            //Derivatives
            //$scope.LM_Deriv_url = "/stock-share-price/future-options/derivatives/" + $scope.scripcode + "/";
            $scope.LM_Deriv_url = $scope.Leftmenudata.EQSEOurl + "derivatives/";
            //SLB
            $scope.LM_SBL_url = $scope.Leftmenudata.EQSEOurl + "slb/";
            //Corp Announements
            //$scope.LM_CropAnn_url = "/corporates/ann.html?scrip=" + $scope.scripcode;
            $scope.LM_CropAnn_url = $scope.Leftmenudata.EQSEOurl + "corp-announcements/";
            //Corp Actions
            $scope.LM_CropAct_url = $scope.Leftmenudata.EQSEOurl + "corp-actions/";
            //Shareholding Pattern
            $scope.LM_ShaPat_url = $scope.Leftmenudata.EQSEOurl + "flag/7/shp/";

            //Unit Shareholding Pattern
            $scope.LM_ShaUnitPat_url = $scope.Leftmenudata.EQSEOurl + "shpunit/";
            //Latest Shareholding Pattern
          //  $scope.LM_latestShaPat_url = $scope.Leftmenudata.EQSEOurl + "shareholding-pattern/";
            $scope.LM_latestShaPat_url = $scope.Leftmenudata.EQSEOurl + "flag/7/shp/";
            //sdd shareholding by shweta
            $scope.LM_sddShaPat_url = $scope.Leftmenudata.EQSEOurl + "sddshareholding-pattern/";
            //Corporate Governance
            //$scope.LM_CropGov_url = "/corporates/Corpgovernane.aspx?scripcode=" + $scope.scripcode + "&flag=7";
           // $scope.LM_CropGov_url = $scope.Leftmenudata.EQSEOurl + "corporate-governance/";
            //as per redmine 151951-->sonam
            //$scope.LM_CropGov_url = $scope.Leftmenudata.EQSEOurl + "corporate-governance/";
            $scope.LM_CropGov_url = $scope.Leftmenudata.EQSEOurl + "flag/7/corporate-governance/";
            //Integrated filing by shweta
            $scope.LM_intgratedfiling_url = $scope.Leftmenudata.EQSEOurl + "integrated-filing-governance/";
            $scope.LM_intgratedfilingfinance_url = $scope.Leftmenudata.EQSEOurl + "integrated-filing-finance/";
            //Investor Complaints
           // $scope.LM_InvComplaints_url = $scope.Leftmenudata.EQSEOurl + "statement-of-investor-complaints/";
            // as per redmine 151951-->sonam
            //$scope.LM_InvComplaints_url = $scope.Leftmenudata.EQSEOurl + "statement-of-investor-complaints/";
            $scope.LM_InvComplaints_url = "/stock-share-price/sic/scripcode/" + $scope.scripcode + "/flag/7/";
            //Related Party Transactions
            //$scope.LM_Party_Transactions_url = $scope.Leftmenudata.EQSEOurl + "related-party-transactions-new/";
            $scope.LM_Party_Transactions_url = "/stock-share-price/rpt/scripcode/" + $scope.scripcode + "/flag/7/";
            //brsr
            $scope.LM_brsr = $scope.Leftmenudata.EQSEOurl + "brsr/";
            //ascr
            $scope.LM_ascr = $scope.Leftmenudata.EQSEOurl + "ascr/"
            //Bulk /  Block deals
            $scope.LM_Bulkblk_url = $scope.Leftmenudata.EQSEOurl + "bulk-block-deals/";
            //Corp Information
            $scope.LM_Cropinfo_url = $scope.Leftmenudata.EQSEOurl + "corp-information/";
            //Peer Group Comparison
            $scope.LM_PeerGrp_url = $scope.Leftmenudata.EQSEOurl + "peer-group-comparison/";
            //Charting
            $scope.LM_Charting_url = "https://charting.bseindia.com/index.html?SYMBOL=" + $scope.scripcode;
            //reasearch reports
            $scope.LM_RR_url = $scope.Leftmenudata.EQSEOurl + "research-reports/";
            //Notices
            $scope.LM_Notice_url = "/markets/MarketInfo/NoticesCirculars.aspx?txtscripcd=" + $scope.scripcode;
            //Research Reports
            $scope.LM_Research_url = $scope.Leftmenudata.EQSEOurl + "research-reports/";
            //
            $scope.LM_Invit_url = $scope.Leftmenudata.EQSEOurl + "additional-info/";
            //Debt / Others
            $scope.LM_Debt_url = $scope.Leftmenudata.EQSEOurl + "debt-most-active-series/";
            //Financials
            $scope.LM_FinRepSpecial_url = $scope.Leftmenudata.EQSEOurl + "financials-results-special/";
            $scope.LM_FinReport_url = $scope.Leftmenudata.EQSEOurl + "financials-results/";
            $scope.LM_FinAnnRepot_url = $scope.Leftmenudata.EQSEOurl + "financials-annual-reports/";
            //
            //Meetings
            $scope.LM_MBM_url = $scope.Leftmenudata.EQSEOurl + "board-meetings/";
            $scope.LM_MSM_url = $scope.Leftmenudata.EQSEOurl + "shareholders-meetings/";
            $scope.LM_MVR_url = $scope.Leftmenudata.EQSEOurl + "voting-results/";
            $scope.LM_MDM_url = $scope.Leftmenudata.EQSEOurl + "Debt_meetingsDetails/";
            //
            //Disclosures
            $scope.LM_DisIT2015_url = $scope.Leftmenudata.EQSEOurl + "disclosures-insider-trading-2015/";
            $scope.LM_DisIT1992_url = $scope.Leftmenudata.EQSEOurl + "disclosures-insider-trading-1992/";
            $scope.LM_DisSAST_url = $scope.Leftmenudata.EQSEOurl + "disclosures-sast/";
            $scope.LM_DisSASTPIT_url = $scope.Leftmenudata.EQSEOurl + "disclosures-sastpit/"; //SDDPIT Html
            $scope.LM_DisPle_url = "/corporates/sastpledge_new.html?scripcd=" + $scope.scripcode;
            $scope.LM_DisSASTAnn_url = "/corporates/Sast_Annual.html?scripcode=" + $scope.scripcode;
            $scope.LM_encumbrance_url = "/corporates/encumbrance.aspx?scripcd=" + $scope.scripcode;
            $scope.LM_DisCPD_url = $scope.Leftmenudata.EQSEOurl + "disclosures-consolidated-pledge-data/";
            $scope.LM_DisSSP_url = $scope.Leftmenudata.EQSEOurl + "disclosures-sdd-sast-promoter/";
            $scope.LM_DisSSNP_url = $scope.Leftmenudata.EQSEOurl + "disclosures-sdd-sast-non-promoter/";
            $scope.LM_DisSSPL_url = $scope.Leftmenudata.EQSEOurl + "disclosures-sdd-sast-pledge/";
            $scope.LM_DisSAST31_url = $scope.Leftmenudata.EQSEOurl + "disclosures-sast-31/";
            $scope.LM_DisintermeDT_url = $scope.Leftmenudata.EQSEOurl + "disclosures-intermediariesDT/";
            $scope.LM_DisintermeCRA_url = $scope.Leftmenudata.EQSEOurl + "disclosures-intermediaries-CRA/";
            $scope.LM_DisintermRatingactn_url = $scope.Leftmenudata.EQSEOurl + "disclosures-intermediaries-RatingAction/";
            $scope.LM_DisPITTradPlan_url = $scope.Leftmenudata.EQSEOurl + "disclosures-PIT-Trading-Plan/";
            $scope.LM_erp_url = $scope.Leftmenudata.EQSEOurl + "intermediaries-ERP/";
            
            // MF PIT Disclosures
            $scope.LM_MFUPSI_url = $scope.Leftmenudata.EQSEOurl + "upsi/";
            $scope.LM_MFOMT_url = $scope.Leftmenudata.EQSEOurl + "Off-market-transaction/";
            $scope.LM_MFTP_url = $scope.Leftmenudata.EQSEOurl + "trading-plan/";
            $scope.LM_MFQDR_url = $scope.Leftmenudata.EQSEOurl + "quarterly-disclosures/";
            $scope.LM_MFEBD_url = $scope.Leftmenudata.EQSEOurl + "event-based-disclosures/";
            //MF Corporate Information
            $scope.LM_MFCICI_url = $scope.Leftmenudata.EQSEOurl + "pit-corp-information";

            $scope.loader.LFloading = false;
            $scope.loader.LFloaded = true;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
        });
    }

    $scope.OpenLoginWindow = function (aid, scripcode) {
        //var aid = $(this).attr('id');
        if (aid == "AtoWL") {
            window.open("https://bseplus.bseindia.com/MyBSE/Default.aspx?flag=WL&scrip_cd=" + scripcode, "search", "toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=yes,resizable=yes,width=800,height=500");
        }
        else if (aid == "AtoPF") {
            window.open("https://bseplus.bseindia.com/MyBSE/Default.aspx?flag=PF&scrip_cd=" + scripcode, "search", "toolbar=no,location=no,directories=no,status=no,menubar=no,scrollbars=yes,resizable=yes,width=800,height=500");
        }
    }

    $scope.fnStockTrading = function () {
        $scope.loader.STState = 'loading';
        $scope.loader.STdelay = false;
        var url = mainapi.newapi_domain + serviceurl.url_StockTrading;
        //$http.post(url, '{"scripcode":"' + $scope.scripcode + '","quotetype":"EQ","flag":""}').then(function successCallback(response) {
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, quotetype: "EQ", flag: "" } }).then(function successCallback(response) {
            $scope.StkTrading = response.data;
            $scope.loader.STState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.STdelay = true;
                $scope.loader.STState = 'loading';
            }
        });
    }

    $scope.fnPriceBand = function () {
        $scope.loader.PBState = 'loading';
        $scope.loader.PBdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl.url_PriceBand;
        //$http.post(url, '{"scripcode":"' + $scope.scripcode + '"}').then(function successCallback(response) {
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode } }).then(function successCallback(response) {
            $scope.PriceBand = response.data;
            $scope.loader.PBState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.PBdelay = true;
                $scope.loader.PBState = 'loading';
            }
        });
    }

    $scope.fnHighlow = function () {
        $scope.loader.HLState = 'loading';
        $scope.loader.HLdelay = false;
        var url = mainapi.newapi_domain + serviceurl.url_Highlow;
        //$http.post(url, '{"scripcode":"' + $scope.scripcode + '","Type":"EQ","flag":"C"}').then(function successCallback(response) {
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, Type: "EQ", flag: "C" } }).then(function successCallback(response) {
            $scope.HLdata = response.data;
            $scope.sliderhigh52wk = $scope.HLdata.Fifty2WkHigh_adj;
            $scope.sliderlow52wk = $scope.HLdata.Fifty2WkLow_adj;
            //$("#WeekSlider").slider("option", { min: parseFloat($scope.sliderlow52wk), max: parseFloat($scope.sliderhigh52wk) });

            $scope.loader.HLState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.HLdelay = true;
                $scope.loader.HLState = 'loading';
            }
        });
    }



    $scope.fn_ScripwiseCautionaryMsg = function () {
        $scope.loader.SCMloading = true;
        $scope.loader.SCMloaded = false;
        var url = mainapi.api_domainLIVE + serviceurl.url_ScripwiseCautionaryMsg;
        //$http.post(url, '{"scripcode":"' + $scope.scripcode + '"}').then(function successCallback(response) {
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode } }).then(function successCallback(response) {
            $scope.CautionaryMsgdata = response.data;
            $scope.loader.SCMloading = false;
            $scope.loader.SCMloaded = true;
            $scope.loader.SCMdelay = false;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SCMdelay = true;
            }
        });
    }



    $scope.intervalFunction = function () {
        $timeout(function () {
            if (document.visibilityState == "visible") {
                $scope.fnPriceBand();
                $scope.fnStockTrading();
                $scope.fnCompanydata();
                $scope.Intervalflag = 1;
                $scope.fn_ScripHeaderData();
                $rootScope.SensexTable();
                $scope.fn_ScripwiseCautionaryMsg();
            }
            $scope.intervalFunction();
        }, 60000)
    };
    // Kick off the interval
    $scope.intervalFunction();

    $scope.recallFunction = function () {
        $timeout(function () {
            if ($scope.loader.PBPdelay == true) { $scope.fnPriceBand(); }
            if ($scope.loader.STdelay == true) { $scope.fnStockTrading(); }
            if ($scope.loader.Cdelay == true) { $scope.fnCompanyname(); }
            if ($scope.loader.CHdelay == true) { $scope.fnScripOHLC(); }
            if ($scope.loader.CDdelay == true) { $scope.fnCompanydata(); }
            if ($scope.loader.NTdelay == true) { $scope.fnNotiftn(); }
            if ($scope.loader.SCMdelay == true) { $scope.fn_ScripwiseCautionaryMsg(); }
            $scope.recallFunction();
        }, 20000)
    };
    $scope.recallFunction();


    $scope.checknullheader = function (entnum) {
        if (entnum == null || entnum == undefined || entnum == "" || entnum == 0)
            return true;
        else
            return false;
    }
    $scope.trustAsHtml = function (string) {
        return $sce.trustAsHtml(string);
    };
}]);
// Function to equity data.
getquote.constant('serviceurl1', {
    url_MarketDepth: 'MarketDepth/w',
    //getquote.constant('url_TabResults', 'TabResults/w');
    url_TabResults: 'TabResults_PAR/w',
    url_SDP: 'SecurityPosition/w',
    url_VRMargin: 'VarMargin/w',
    url_PeerGpComp_eq: 'EQPeerGp/w',
    url_PriceGL: 'PriceGainLoss_New/w',
    url_StockVsSensex: 'ChangeInStockVsSensex/w',
    url_StockVsRelated: 'ChangeInStockVsBankex/w',
    url_BulkblockDeal: 'HomeBulkblockDealNew/w'
});
getquote.controller('equityController', ['serviceurl1', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function equityController(serviceurl1, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {
    /*Google Analytics new code*/
    //var url_hrefSeries = $(location).attr('href');
    //(function (i, s, o, g, r, a, m) {
    //    i['GoogleAnalyticsObject'] = r; i[r] = i[r] || function () {
    //        (i[r].q = i[r].q || []).push(arguments)
    //    }, i[r].l = 1 * new Date(); a = s.createElement(o),
    //        m = s.getElementsByTagName(o)[0]; a.async = 1; a.src = g; m.parentNode.insertBefore(a, m)
    //})(window, document, 'script', 'https://www.google-analytics.com/analytics.js', 'ga');
    //ga('create', 'UA-27569176-1', 'auto');
    //ga('send', 'pageview');
    //ga('set', 'page', url_hrefSeries);
    /*Google Analytics new code*/

    $scope.graphtype = 0;
    $scope.loader = {
        GPloading: true,
        GPloaded: false,
        CAState: 'loading',
        GPState: 'loading',
        MDState: 'loading',
        NState: 'loading',
        RState: 'loading',
        SState: 'loading',
        BState: 'loading',
        SDPState: 'loading',
        SDPState1: 'loading',
        //SDPState2: 'loading',
        //SDPState3: 'loading',
        VRState: 'loading',
        PBState: 'loading',
        CAdelay: false,
        GPdelay: false,
        MDdelay: false,
        Ndelay: false,
        delay: false,
        SDPdelay: false,
        SDPdelay1: false,
        //SDPdelay2: false,
        //SDPdelay3: false,
        VRdelay: false,
        VRdelay: false,
        VRState: 'loading',
        BlState: 'loading',
    };
    $scope.AddScrip = function (Code) {
        $scope.sc = Code;
        if (localStorage) {
            var nscr;
            var scr = localStorage.getItem('recentview');
            if (scr != 'undefined' && scr != null && scr != "") {
                var scrip = scr.split(',');

                if (scrip.length > 10) {
                    var k = scrip.length - 10;
                    for (var i = k; i < scrip.length; i++) {
                        if (Code != scrip[i]) {
                            if (i == k) {
                                nscr = scrip[i];
                            }
                            else {
                                if (nscr == undefined) { nscr = scrip[i]; }
                                else {
                                    nscr = nscr + "," + scrip[i];
                                }
                            }
                        }
                    }
                }
                else {
                    for (var i = 0; i < scrip.length; i++) {
                        if (Code != scrip[i]) {
                            if (i == 0) {
                                nscr = scrip[i];
                            }
                            else {
                                if (nscr == undefined) { nscr = scrip[i]; }
                                else { nscr = nscr + "," + scrip[i]; }
                            }
                        }
                    }
                }
                if (nscr == undefined)
                    nscr = $scope.sc;
                else
                    nscr = nscr + "," + $scope.sc;
            }
            else {
                nscr = $scope.sc;
            }
            nscr.replace(/undefined/g, "000000");
            localStorage.setItem('recentview', nscr);
        }
        else { alert("not suppport"); }
    };
    //$scope.AddScrip($scope.scripcode);
    $scope.fnsensexGraph = function (code, flag, seriesid) {

        $scope.graphtype = flag;
        Graph(code, flag, seriesid);//'0', 'R');
        $scope.loader.GPloading = gloding;
        $scope.loader.GPloaded = gloded;
        $scope.loader.GPdelay = gdelay;
        if (flag == "1") {
            $scope.graphtype = "0";
        }
    }
    // $scope.fnsensexGraph($scope.scripcode, $scope.graphtype, '');
    // console.log( $scope.fnsensexGraph($scope.scripcode, $scope.graphtype, ''));
    $scope.fnMarketDepth = function () {
        $scope.loader.MDState = 'loading';
        $scope.loader.MDdelay = false;
        var url = mainapi.api_domainRealTime + serviceurl1.url_MarketDepth;
        // $http.post(url, '{"scripcode":"' + $scope.scripcode + '","quotetype":"EQ","flag":""}').then(function successCallback(response) {
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, quotetype: "EQ", flag: "" } }).then(function successCallback(response) {
            $scope.MarketDepth = response.data;
            $scope.loader.MDState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.MDdelay = true;
                $scope.loader.MDState = 'loading';
            }
        });
    }
    $scope.MktStreamer = function () {
        document.getElementById('DivStreamer').innerHTML = "<iframe style='width:100%' id='ifrmStream' src='../Eqstreamer/stkreach.html?scrip=" + $scope.scripcode + "' frameborder='0'></iframe>";

        $('#DivStreamer').draggable();
    }
    $scope.fnNews = function () {
        $scope.loader.NState = 'loading';
        $scope.loader.Ndelay = false;
        $("#anews").attr("aria-expanded", !0);
        $("#aac").attr("aria-expanded", !1);
        $("#abulk").attr("aria-expanded", !1);
        var url = mainapi.api_domainLIVE + serviceurl1.url_TabResults;
        //$http.post(url, '{"scripcode":"' + $scope.scripcode + '","tabtype":"NEWS"}').then(function successCallback(response) {
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, tabtype: "NEWS" } }).then(function successCallback(response) {
            $scope.NewsData = JSON.parse(response.data);
            $scope.loader.NState = 'loaded';

        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.Ndelay = true;
                $scope.loader.NState = 'loading';
            }
        });
    }
    $scope.View = "inCR";
    $scope.fnTabResult = function (tabindex) {
        $scope.tab = tabindex;
        $("#tabres").attr("aria-expanded", !1);
        $("#tabshp").attr("aria-expanded", !1);
        $("#tabtechnical").attr("aria-expanded", !1);
        $("#analytics").attr("aria-expanded", !1);
        if ($scope.tab == "SHP") {
            $scope.loader.SState = 'loading';
        }
        if ($scope.tab == "BULK") {
            $scope.loader.BState = 'loading';
        }
        if ($scope.tab == "CA") {
            $scope.loader.CAState = 'loading'
        }
        if ($scope.tab == "RESULTS") {
            $scope.loader.RState = 'loading'
        }
        if ($scope.tab == "tech") {
            $("#tabtechnical").attr("aria-expanded", !0);
        }
        if ($scope.tab == "analy") {
            $scope.loader.SDPState1 = 'loading';
            //$scope.loader.SDPState2 = 'loading';
            //$scope.loader.SDPState3 = 'loading';
            $("#analytics").attr("aria-expanded", !0);
        }
        if ($scope.tab == "BLOCK") {
            $scope.loader.BlState = 'loading';
        }
        $scope.loader.delay = false;
        if ($scope.tab == "BLOCK") {
            var url = mainapi.api_domainLIVE + serviceurl1.url_BulkblockDeal;
            //$http.post(url, '{"scripcode":"' + $scope.scripcode + '","tabtype":"' + $scope.tab + '"}').then(function successCallback(response) {
            $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode } }).then(function successCallback(response) {
                if ($scope.tab == "SHP") {
                    $scope.TabResult = response.data;
                    $scope.loader.SState = 'loaded';
                    $("#tabshp").attr("aria-expanded", !0);
                    $("#tabtechnical").attr("aria-expanded", !1);
                    $("#tabres").attr("aria-expanded", !1);
                    $("#analytics").attr("aria-expanded", !1);
                }
                else {


                    if ($scope.tab == "BLOCK") {
                        $scope.BlTabResult = response.data.Table2;
                        $scope.loader.BlState = 'loaded';
                        $("#ablock").attr("aria-expanded", !0);
                        $("#anews").attr("aria-expanded", !1);
                        $("#aac").attr("aria-expanded", !1);
                        $("#abulk").attr("aria-expanded", !1);
                    }
                }
            }, function errorCallback(response) {
                $scope.status = response.status + "_" + response.statusText;
                if (response.status == (500 || 503)) {
                    $scope.loader.delay = true;

                    if ($scope.tab == "BLOCK") {
                        $scope.loader.BlState = 'loading';
                    }
                }
            });
        }
        else {
            var url = mainapi.api_domainLIVE + serviceurl1.url_TabResults;
            //$http.post(url, '{"scripcode":"' + $scope.scripcode + '","tabtype":"' + $scope.tab + '"}').then(function successCallback(response) {
            $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, tabtype: $scope.tab } }).then(function successCallback(response) {
                if ($scope.tab == "SHP") {
                    $scope.TabResult = response.data;
                    $scope.loader.SState = 'loaded';
                    $("#tabshp").attr("aria-expanded", !0);
                    $("#tabtechnical").attr("aria-expanded", !1);
                    $("#tabres").attr("aria-expanded", !1);
                    $("#analytics").attr("aria-expanded", !1);
                }
                else {

                    if ($scope.tab == "BULK") {
                        $scope.BTabResult = JSON.parse(response.data);
                        $scope.loader.BState = 'loaded';
                        $("#abulk").attr("aria-expanded", !0);
                        $("#anews").attr("aria-expanded", !1);
                        $("#aac").attr("aria-expanded", !1);
                        $("#ablock").attr("aria-expanded", !1);
                    }
                    if ($scope.tab == "CA") {
                        $scope.CTabResult = JSON.parse(response.data);
                        $scope.loader.CAState = 'loaded';
                        $("#aac").attr("aria-expanded", !0);
                        $("#anews").attr("aria-expanded", !1);
                        $("#abulk").attr("aria-expanded", !1);
                        $("#ablock").attr("aria-expanded", !1);
                    }
                    if ($scope.tab == "RESULTS") {

                        $scope.RTabResult = JSON.parse(response.data);
                        console.log($scope.RTabResult);
                        $scope.loader.RState = 'loaded';
                        $("#tabres").attr("aria-expanded", !0);
                        $("#tabshp").attr("aria-expanded", !1);
                        $("#tabtechnical").attr("aria-expanded", !1);
                        $("#analytics").attr("aria-expanded", !1);

                    }
                    if ($scope.tab == "analy") {
                        $scope.fnPriceGL();
                        //$scope.fnStockVsSensex();
                        //$scope.fnStockVsRelated();
                        $scope.loader.SDPState1 = 'loaded';
                        //$scope.loader.SDPState2 = 'loaded';
                        //$scope.loader.SDPState3 = 'loaded';
                        $scope.loader.RState = 'loaded';
                        $("#tabres").attr("aria-expanded", !1);
                        $("#tabshp").attr("aria-expanded", !1);
                        $("#tabtechnical").attr("aria-expanded", !1);
                        $("#analytics").attr("aria-expanded", !0);

                    }
                }
            }, function errorCallback(response) {
                $scope.status = response.status + "_" + response.statusText;
                if (response.status == (500 || 503)) {
                    $scope.loader.delay = true;
                    if ($scope.tab == "SHP") {
                        $scope.loader.SState = 'loading';
                    }
                    if ($scope.tab == "BULK") {
                        $scope.loader.BState = 'loading';
                    }
                    if ($scope.tab == "CA") {
                        $scope.loader.CAState = 'loading';
                    }
                    if ($scope.tab == "RESULTS") {
                        $scope.loader.RState = 'loading';
                    }
                    if ($scope.tab == "analy") {
                        $scope.loader.SDPState1 = 'loading';
                        //$scope.loader.SDPState2 = 'loading';
                        //$scope.loader.SDPState3 = 'loading';
                    }

                }
            });
        }
    }
    $scope.SetView = function (VW) {
        $scope.View = VW;
    }
    $scope.fnSDP = function () {
        $("#asdp").attr("aria-expanded", !0);
        $("#avrnm").attr("aria-expanded", !1);
        $scope.loader.SDPState = 'loading';
        $scope.loader.SDPdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl1.url_SDP;
        //$http.post(url, '{"scripcode":"' + $scope.scripcode + '","quotetype":"EQ"}').then(function successCallback(response) {
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, quotetype: "EQ" } }).then(function successCallback(response) {
            $scope.SDPdata = JSON.parse(response.data);
            $scope.loader.SDPState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SDPdelay = true;
                $scope.loader.SDPState = 'loading';
            }
        });
    }

    $scope.fnPriceGL = function () {
        $scope.loader.SDPState1 = 'loading';
        $scope.loader.SDPdelay1 = false;
        var url = mainapi.api_domainLIVE + serviceurl1.url_PriceGL;
        //$http.post(url, '{"scripcode":"' + $scope.scripcode + '","quotetype":"EQ"}').then(function successCallback(response) {
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode } }).then(function successCallback(response) {
            $scope.PriceGL = response.data;
            $scope.IndexCode = $scope.PriceGL.Headers[0].Index_name_1;

        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SDPdelay1 = true;
                $scope.loader.SDPState1 = 'loading';
            }
        });
    }

    //$scope.fnStockVsSensex = function () {
    //    $scope.loader.SDPState2 = 'loading';
    //    $scope.loader.SDPdelay2 = false;
    //    var url = $injector.get('api_domainLIVE') + $injector.get('url_StockVsSensex');
    //    //$http.post(url, '{"scripcode":"' + $scope.scripcode + '","quotetype":"EQ"}').then(function successCallback(response) {
    //    $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode } }).then(function successCallback(response) {
    //        $scope.StockVsSensex = response.data;
    //        $scope.loader.SDPState2 = 'loaded';
    //    }, function errorCallback(response) {
    //        $scope.status = response.status + "_" + response.statusText;
    //        if (response.status == (500 || 503)) {
    //            $scope.loader.SDPdelay2 = true;
    //            $scope.loader.SDPState2 = 'loading';
    //        }
    //    });
    //}

    //$scope.fnStockVsRelated = function () {
    //    $scope.loader.SDPState3 = 'loading';
    //    $scope.loader.SDPdelay3 = false;
    //    var url = $injector.get('api_domainLIVE') + $injector.get('url_StockVsRelated');
    //    //$http.post(url, '{"scripcode":"' + $scope.scripcode + '","quotetype":"EQ"}').then(function successCallback(response) {
    //    $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode} }).then(function successCallback(response) {
    //        $scope.StockVsRelated = response.data;
    //        $scope.loader.SDPState3 = 'loaded';
    //    }, function errorCallback(response) {
    //        $scope.status = response.status + "_" + response.statusText;
    //        if (response.status == (500 || 503)) {
    //            $scope.loader.SDPdelay3 = true;
    //            $scope.loader.SDPState3 = 'loading';
    //        }
    //    });
    //}

    $scope.trustAsHtml = function (string) {
        return $sce.trustAsHtml(string);
    };
    $scope.fnVRMargin = function () {
        $("#asdp").attr("aria-expanded", !1);
        $("#avrnm").attr("aria-expanded", !0);
        $scope.loader.VRState = 'loading';
        $scope.loader.VRdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl1.url_VRMargin;
        //$http.post(url, '{"scripcode":"' + $scope.scripcode + '","getquotetype":"EQ"}').then(function successCallback(response) {
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, getquotetype: "EQ" } }).then(function successCallback(response) {
            $scope.VRMdata = response.data;
            $scope.loader.VRState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.VRdelay = true;
                $scope.loader.VRState = 'loading';
            }
        });
    }
    $scope.intervalFunction = function () {
        $timeout(function () {
            if (document.visibilityState == "visible") {
                $scope.fnsensexGraph($scope.scripcode, $scope.graphtype, '');
                $scope.fnMarketDepth();
                $scope.fnNews();
                //$scope.fnTabResult($scope.tab);
                $scope.fnHighlow();
                $scope.fnVRMargin();
                $scope.fnSDP();
            }
            $scope.intervalFunction();
        }, 60000);
    };
    // Kick off the interval
    $scope.intervalFunction();
    $scope.recallFunction = function () {
        $timeout(function () {
            if ($scope.loader.delay == true) { $scope.fnTabResult($scope.tab); }
            if ($scope.loader.MDdelay == true) { $scope.fnMarketDepth(); }

            if ($scope.loader.Ndelay == true) { $scope.fnNews(); }
            if ($scope.loader.HLdelay == true) { $scope.fnHighlow(); }
            if ($scope.loader.VRdelay == true) { $scope.fnVRMargin(); }
            if ($scope.loader.SDPdelay == true) { $scope.fnSDP(); }

            if ($scope.loader.GPdelay == true) { $scope.fnsensexGraph($scope.scripcode, $scope.graphtype, ''); }
            $scope.recallFunction();
        }, 20000)
    };
    $scope.recallFunction();
    $scope.checknull = function (entnum) {
        if (entnum == null || entnum == undefined || entnum == "" || entnum == 0)
            return true;
        else
            return false;
    }
    $scope.sign = function (entnum) {
        try {
            if (entnum == null || entnum == undefined || entnum == "") {
                return "--";
            }
            else {
                if (parseFloat(entnum) > 0)
                    return "+" + entnum;
                else
                    return entnum;
            }
        }
        catch (e) {
            console.log(e);
            return entnum;
        }
    }
    $scope.ViewPG = "in Cr.";
    $scope.ViewinPG = "View in (Million)";
    $scope.fn_PeerGrp = function () {
        var url = mainapi.api_domainLIVE + serviceurl1.url_PeerGpComp_eq;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, scripcomare: '' } }).then(function successCallback(response) {
            $scope.PeerGpComp = response.data;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
        });
    }
    $scope.fn_Viewin = function () {
        if ($scope.ViewPG == "in Cr.") {
            $scope.ViewinPG = "View in (Cr.)";
            $scope.ViewPG = "in Million";
            for (var i = 0; i < $scope.PeerGpComp.Table.length; i++) {
                if (!$scope.checknull($scope.PeerGpComp.Table[i].Revenue))
                    $scope.PeerGpComp.Table[i].Revenue = $scope.PeerGpComp.Table[i].Revenue * 10;
                if (!$scope.checknull($scope.PeerGpComp.Table[i].PAT))
                    $scope.PeerGpComp.Table[i].PAT = $scope.PeerGpComp.Table[i].PAT * 10;
                if (!$scope.checknull($scope.PeerGpComp.Table[i].Equity))
                    $scope.PeerGpComp.Table[i].Equity = $scope.PeerGpComp.Table[i].Equity * 10;
            }
        }
        else if ($scope.ViewPG == "in Million") {
            $scope.ViewinPG = "View in (Million)";
            $scope.ViewPG = "in Cr.";
            for (var i = 0; i < $scope.PeerGpComp.Table.length; i++) {
                if (!$scope.checknull($scope.PeerGpComp.Table[i].Revenue))
                    $scope.PeerGpComp.Table[i].Revenue = $scope.PeerGpComp.Table[i].Revenue / 10;
                if (!$scope.checknull($scope.PeerGpComp.Table[i].PAT))
                    $scope.PeerGpComp.Table[i].PAT = $scope.PeerGpComp.Table[i].PAT / 10;
                if (!$scope.checknull($scope.PeerGpComp.Table[i].Equity))
                    $scope.PeerGpComp.Table[i].Equity = $scope.PeerGpComp.Table[i].Equity / 10;
            }
        }
    }
    $scope.fn_EqTitle = function () {
        var strkeywords = "";
        var strDescp = "";
        var strRawUrl = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
        var strRawUrl1 = $location.absUrl().replace(/[\\#,+()$~%"*<>{};]/g, '_');
        var strArray = strRawUrl.split('/');
        if (strArray != null && strArray.length > 5) {
            strkeywords = "<meta name='keywords' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " share price, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " share price, " + strArray[6] + " share price, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " live stock price, " + $rootScope.camelize(strArray[5].replace(" - ", " ").replace(" - ", " ")) + " live stock price,  " + strArray[6] + " live stock price, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " stock price today, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " stock price today,  " + strArray[6] + " live stock price, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " latest updates, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " news, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " quotes, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " graph,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " chart,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " 52 week high,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " 52 week low,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  market  capitalisation,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  buy price, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  buy quantity,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " sell price,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " sell quantity, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " bid , " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " offer, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " intraday price,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Net profit margin, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " EPS, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " PE, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Price Earnings, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " PB, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Price to Book Value, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " ROE, Return on Equity, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Industry, BSE, BSEIndia'>";
            strkeywords = strkeywords.replace("-", " ");
            strDescp = "<meta name='description' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Live BSE Share Price today, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " latest news,  " + strArray[6] + "  announcements. " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " financial results,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " shareholding, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " annual reports, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " pledge, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " insider trading and compare with peer companies.'>";
            strDescp = strDescp.replace("-", " ");
            $('meta[name=description]').remove();
            $('meta[name=keywords]').remove();
            $(strkeywords).appendTo(document.head);
            $(strDescp).appendTo(document.head);

            var strtwittertitle = "<meta name='twitter:title' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " share price, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " share price, " + strArray[6] + " share price, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " live stock price, " + $rootScope.camelize(strArray[5].replace(" - ", " ").replace(" - ", " ")) + " live stock price,  " + strArray[6] + " live stock price, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " stock price today, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " stock price today,  " + strArray[6] + " live stock price, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " latest updates, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " news, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " quotes, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " graph,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " chart,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " 52 week high,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " 52 week low,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  market  capitalisation,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  buy price, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  buy quantity,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " sell price,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " sell quantity, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " bid , " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " offer, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " intraday price,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Net profit margin, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " EPS, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " PE, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Price Earnings, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " PB, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Price to Book Value, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " ROE, Return on Equity, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Industry, BSE, BSEIndia'>";
            strtwittertitle = strtwittertitle.replace("-", " ");
            $('meta[name="twitter:title"]').remove();
            $(strtwittertitle).appendTo(document.head);

            var strtwitterdes = "<meta name='twitter:description' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Live BSE Share Price today, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " latest news,  " + strArray[6] + "  announcements. " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " financial results,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " shareholding, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " annual reports, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " pledge, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " insider trading and compare with peer companies.'>";
            strtwitterdes = strtwitterdes.replace("-", " ");
            $('meta[name="twitter:description"]').remove();
            $(strtwitterdes).appendTo(document.head);


            $('meta[name="twitter:url"]').remove();
            $("head").append("<meta name='twitter:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:url"]').remove();
            $("head").append("<meta property='og:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:title"]').remove();
            $("head").append("<meta property='og:title' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " share price, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " share price, " + strArray[6] + " share price, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " live stock price, " + $rootScope.camelize(strArray[5].replace(" - ", " ").replace(" - ", " ")) + " live stock price,  " + strArray[6] + " live stock price, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " stock price today, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " stock price today,  " + strArray[6] + " live stock price, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " latest updates, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " news, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " quotes, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " graph,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " chart,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " 52 week high,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " 52 week low,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  market  capitalisation,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  buy price, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  buy quantity,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " sell price,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " sell quantity, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " bid , " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " offer, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " intraday price,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Net profit margin, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " EPS, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " PE, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Price Earnings, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " PB, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Price to Book Value, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " ROE, Return on Equity, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Industry, BSE, BSEIndia'>");

            $('meta[property="og:description"]').remove();
            $("head").append("<meta property='og:description' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Live BSE Share Price today, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " latest news,  " + strArray[6] + "  announcements. " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " financial results,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " shareholding, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " annual reports, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " pledge, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " insider trading and compare with peer companies.'>");
        }
        document.title = $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Live Stock Price , " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Live Share Price, " + strArray[6] + " | BSE ";
    }
    $scope.$on('DayOHLC', function (event, args) {
        if (args.High != undefined && args.Low != undefined && args.LTP != undefined) {
            $scope.sliderlow = args.Low;
            $scope.sliderhigh = args.High;
            $("#DaySlider").slider("option", { min: parseFloat(args.Low), max: parseFloat(args.High) });
            $("#DaySlider").slider("option", "value", parseFloat(args.LTP));
            $("#WeekSlider").slider("option", "value", parseFloat(args.LTP));
            var median = (parseFloat(args.High) + parseFloat(args.Low)) / 2;
            if (median <= parseFloat(args.LTP)) {
                $("#DaySlider").slider("option", "classes.ui-slider-handle", "slidhandgreen");
            }
            else { $("#DaySlider").slider("option", "classes.ui-slider-handle", "slidhandred"); }

            if ($scope.sliderhigh52wk != undefined && $scope.sliderlow52wk != undefined) {
                var median2 = (parseFloat($scope.sliderhigh52wk) + parseFloat($scope.sliderlow52wk)) / 2;
                if (median2 <= parseFloat(args.LTP)) {
                    $("#WeekSlider").slider("option", "classes.ui-slider-handle", "slidhandgreen");
                }
                else { $("#WeekSlider").slider("option", "classes.ui-slider-handle", "slidhandred"); }
            }
        }
    });
}]);

//Fuction for bulk block deal
getquote.constant('serviceurl2', {
    url_Bulkblkdeal: "BulkblockDeal/w",
    url_DwnldExcelbulkblock: 'BulkblockDownload/w'
});

getquote.controller('eqbulkblockController', ['serviceurl2', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqbulkblockController(serviceurl2, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {



    $scope.loader = {

        BBState: 'loading',
        BBdelay: false,
    };


    $scope.FromDate = '';//null;
    $scope.ToDate = '';//null;
    $scope.Dealtype = "1";
    $scope.totalItems = 0;
    $scope.currentPage = 1;
    $scope.itemsPerPage = 50;
    $scope.maxSize = 5; //Number of pager buttons to show

    $scope.fn_Bulkblkdeal = function () {
        $scope.Dealtype = $("input[name='dealtype']:checked").val();
        $scope.loader.BBState = 'loading';
        $scope.loader.BBdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl2.url_Bulkblkdeal;
        $http({ url: url, method: "GET", params: { type: $scope.Dealtype, scripcode: $scope.scripcode, fromdt: $scope.FromDate, todt: $scope.ToDate } }).then(function successCallback(response) {
            $scope.BulkBlkDl = response.data;
            $scope.loader.BBState = 'loaded';
            $scope.totalItems = $scope.BulkBlkDl.Table.length;
            $scope.currentPage = 1;
            $scope.DealTypelbl = ($scope.Dealtype == "1") ? "Bulk Deal" : "Block Deal";
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.BBdelay = true;
                $scope.loader.BBState = 'loading';
            }
        });
    }

    $scope.fn_submit_bb = function () {
        if ($scope.FromDate != "" && $scope.ToDate != "") {
            var fmdt = new Date($scope.FromDate.split('/')[2], $scope.FromDate.split('/')[1] - 1, $scope.FromDate.split('/')[0]);
            var todt = new Date($scope.ToDate.split('/')[2], $scope.ToDate.split('/')[1] - 1, $scope.ToDate.split('/')[0]);
            if (fmdt > todt) {
                alert('From date should be less than To date'); return;
            }
            else {
                $scope.fn_Bulkblkdeal();
            }
        }
        else if ($scope.FromDate != "" && $scope.ToDate == "") {
            alert('Please enter From Date');
        }
        else if ($scope.FromDate == "" && $scope.ToDate != "") {
            alert('Please enter To Date');
        }
        else { $scope.fn_Bulkblkdeal(); }
    }

    $scope.fn_downloadexcel = function () {

        var url = mainapi.api_domainLIVE + serviceurl2.url_DwnldExcelbulkblock + "?&type=" + $scope.Dealtype + "&scripcode=" + $scope.scripcode + "&fromdt=" + $scope.FromDate + "&todt=" + $scope.ToDate;
        window.open(url, "_self");
    }

    $scope.fn_blkTitle = function () {
        var strkeywords = "";
        var strDescp = "";
        var strRawUrl = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
        var strRawUrl1 = $location.absUrl().replace(/[\\#,+()$~%"*<>{};]/g, '_');
        var strArray = strRawUrl.split('/');
        if (strArray != null && strArray.length > 5) {
            strkeywords = "<meta name='keywords' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Bulk Deals, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Block Deals, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Bulk Deals, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Block Deals, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Large trades, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " large deals, BSE, BSEIndia'/>";
            strkeywords = strkeywords.replace("-", " ");
            strDescp = "<meta name='description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Bulk Deals, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Block Deals '/>";
            strDescp = strDescp.replace("-", " ");
            $('meta[name=description]').remove();
            $('meta[name=keywords]').remove();
            $(strkeywords).appendTo(document.head);
            $(strDescp).appendTo(document.head);

            var strtwittertitle = "<meta name='twitter:title' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Bulk Deals, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Block Deals, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Bulk Deals, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Block Deals, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Large trades, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " large deals, BSE, BSEIndia'/>";
            strtwittertitle = strtwittertitle.replace("-", " ");
            $('meta[name="twitter:title"]').remove();
            $(strtwittertitle).appendTo(document.head);

            var strtwitterdes = "<meta name='twitter:description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Bulk Deals, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Block Deals '/>";
            strtwitterdes = strtwitterdes.replace("-", " ");
            $('meta[name="twitter:description"]').remove();
            $(strtwitterdes).appendTo(document.head);

            $('meta[name="twitter:url"]').remove();
            $("head").append("<meta name='twitter:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:url"]').remove();
            $("head").append("<meta property='og:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:title"]').remove();
            $("head").append("<meta property='og:title' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Bulk Deals, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Block Deals, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Bulk Deals, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Block Deals, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Large trades, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " large deals, BSE, BSEIndia'/>");

            $('meta[property="og:description"]').remove();
            $("head").append("<meta property='og:description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Bulk Deals, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Block Deals '/>");
        }
        document.title = $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Bulk Deals, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Block Deals |BSE ";
    }

}]);
//Function for finacial Reports
getquote.constant('serviceurl3', {
    url_reports: 'GetReportNewFor_Result/w',
    url_annreportnew: 'financeresult/w'
});

getquote.controller('eqreportController', ['serviceurl3', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqreportController(serviceurl3, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {


    $scope.loader = {
        REState: 'loading',
        REdelay: false,
    };

    $scope.View = 'inCr';

    $scope.fn_finreport = function () {
        $scope.loader.REState = 'loading';
        $scope.loader.REdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl3.url_reports;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode } }).then(function successCallback(response) {
            $scope.reportData = response.data;
            $scope.loader.REState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.REdelay = true;
                $scope.loader.REState = 'loading';
            }
        });
    }
    $scope.fn_changeView = function () {
        if ($scope.View == 'inCr') {
            $scope.View = 'inM';
            document.getElementById('viewin').innerHTML = "View in (Cr.)";
        }
        else {
            $scope.View = 'inCr';
            document.getElementById('viewin').innerHTML = "View in (Million)";
        }
    }

    $scope.trustAsHtml = function (string) {
        return $sce.trustAsHtml(string);
    };

    $scope.fnanualTab = function (tabindex) {
        $scope.tab = tabindex;
        $("#aanualtrd").attr("aria-expanded", !1);
        $("#atrd").attr("aria-expanded", !1);

        if ($scope.tab == "trd") {
            $("#atrd").attr("aria-expanded", !0);
        }
        if ($scope.tab == "atrd") {
            $("#aanualtrd").attr("aria-expanded", !0);
        }

    }

    $scope.fn_reptTitle = function () {
        var strkeywords = "";
        var strDescp = "";
        var strRawUrl = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
        var strRawUrl1 = $location.absUrl().replace(/[\\#,+()$~%"*<>{};]/g, '_');
        var strArray = strRawUrl.split('/');
        if (strArray != null && strArray.length > 5) {
            strkeywords = "<meta name='keywords' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " latest results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " financial results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " quarterly results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " annual results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " audited results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " unaudited results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Standalone results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Consolidated results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Segment wise Results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Income, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Revenue, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " PAT, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Profit after Tax, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Net Profit," + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " EPS, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Earnings per Share , BSE, BSEIndia'>";
            strkeywords = strkeywords.replace("-", " ");
            strDescp = "<meta name='description' content='" + "Quarterly & Annual Financial Results of  " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Check latest quarterly results and compare financial performance over past years. Get latest Standalone, Consolidated and Segment wise financial results.'>";
            strDescp = strDescp.replace("-", " ");
            $('meta[name=description]').remove();
            $('meta[name=keywords]').remove();
            $(strkeywords).appendTo(document.head);
            $(strDescp).appendTo(document.head);

            var strtwittertitle = "<meta name='twitter:title' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " latest results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " financial results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " quarterly results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " annual results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " audited results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " unaudited results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Standalone results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Consolidated results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Segment wise Results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Income, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Revenue, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " PAT, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Profit after Tax, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Net Profit," + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " EPS, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Earnings per Share , BSE, BSEIndia'>";
            strtwittertitle = strtwittertitle.replace("-", " ");
            $('meta[name="twitter:title"]').remove();
            $(strtwittertitle).appendTo(document.head);

            var strtwitterdes = "<meta name='twitter:description' content='" + "Quarterly & Annual Financial Results of  " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Check latest quarterly results and compare financial performance over past years. Get latest Standalone, Consolidated and Segment wise financial results.'>";
            strtwitterdes = strtwitterdes.replace("-", " ");
            $('meta[name="twitter:description"]').remove();
            $(strtwitterdes).appendTo(document.head);

            $('meta[name="twitter:url"]').remove();
            $("head").append("<meta name='twitter:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:url"]').remove();
            $("head").append("<meta property='og:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:title"]').remove();
            $("head").append("<meta property='og:title' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " latest results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " financial results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " quarterly results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " annual results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " audited results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " unaudited results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Standalone results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Consolidated results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Segment wise Results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Income, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Revenue, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " PAT, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Profit after Tax, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Net Profit," + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " EPS, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Earnings per Share , BSE, BSEIndia'>");

            $('meta[property="og:description"]').remove();
            $("head").append("<meta property='og:description' content='" + "Quarterly & Annual Financial Results of  " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Check latest quarterly results and compare financial performance over past years. Get latest Standalone, Consolidated and Segment wise financial results.'>");
        }
        document.title = $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Financial Results – Quarterly & Annual, Quarterly Trends, Annual Trends |BSE"
    }

    $rootScope.$on('$includeContentLoaded', function (event, url) {
        //console.log(event);
        //console.log(url);
        if (url == '/GetQuote/stk_report.html') {
            $('#collapse2').removeClass("panel-collapse collapse");
            $('#collapse2').addClass("panel-collapse collapse in");
            $('#l61').removeClass("panel panel-active");
            $('#l61').addClass("list-group-item");
            var cls = $('#collapse2').attr('class');
            if (cls == 'panel-collapse collapse in') {
                $('#l61').removeClass("list-group-item");
                $('#l61').addClass("panel panel-active");
                $('#l61').parent().addClass("divpanel-ative");
                $('#collapse2').css('display', 'block');
            }
        }
    });

    $scope.fn_annreportnew = function () {
        $scope.loader.ARState = 'loading';
        $scope.loader.ARdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl3.url_annreportnew;
        //var url = 'http://localhost:56980/api/' + serviceurl3.url_annreportnew;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode } }).then(function successCallback(response) {
            $scope.resultData = response.data;
            $scope.loader.ARState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.ARdelay = true;
                $scope.loader.ARState = 'loading';
            }
        });
    }
}]);
//Function for finacial Reports special
getquote.constant('serviceurl4', {
    url_reports_special: 'CorprateResult/w'
});

getquote.controller('eqreportspecialController', ['serviceurl4', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqreportspecialController(serviceurl4, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {


    $scope.loader = {
        REState: 'loading',
        REdelay: false,
    };
    $scope.fn_finreportspecial = function () {
        $scope.loader.REState = 'loading';
        $scope.loader.REdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl4.url_reports_special;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode } }).then(function successCallback(response) {
            $scope.reportDataspecial = response.data;
            $scope.loader.REState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.REdelay = true;
                $scope.loader.REState = 'loading';
            }
        });
    }

    $scope.trustAsHtml = function (string) {
        return $sce.trustAsHtml(string);
    };
    $scope.fn_reptspecialTitle = function () {
        var strkeywords = "";
        var strDescp = "";
        var strRawUrl = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
        var strRawUrl1 = $location.absUrl().replace(/[\\#,+()$~%"*<>{};]/g, '_');
        var strArray = strRawUrl.split('/');
        if (strArray != null && strArray.length > 5) {
            strkeywords = "<meta name='keywords' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " latest results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " financial results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " quarterly results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " annual results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " audited results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " unaudited results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Standalone results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Consolidated results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Segment wise Results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Income, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Revenue, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " PAT, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Profit after Tax, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Net Profit," + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " EPS, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Earnings per Share , BSE, BSEIndia'>";
            strkeywords = strkeywords.replace("-", " ");
            strDescp = "<meta name='description' content='" + "Quarterly & Annual Financial Results of  " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Check latest quarterly results and compare financial performance over past years. Get latest Standalone, Consolidated and Segment wise financial results.'>";
            strDescp = strDescp.replace("-", " ");
            $('meta[name=description]').remove();
            $('meta[name=keywords]').remove();
            $(strkeywords).appendTo(document.head);
            $(strDescp).appendTo(document.head);

            var strtwittertitle = "<meta name='twitter:title' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " latest results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " financial results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " quarterly results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " annual results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " audited results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " unaudited results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Standalone results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Consolidated results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Segment wise Results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Income, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Revenue, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " PAT, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Profit after Tax, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Net Profit," + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " EPS, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Earnings per Share , BSE, BSEIndia'>";
            strtwittertitle = strtwittertitle.replace("-", " ");
            $('meta[name="twitter:title"]').remove();
            $(strtwittertitle).appendTo(document.head);

            var strtwitterdes = "<meta name='twitter:description' content='" + "Quarterly & Annual Financial Results of  " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Check latest quarterly results and compare financial performance over past years. Get latest Standalone, Consolidated and Segment wise financial results.'>";
            strtwitterdes = strtwitterdes.replace("-", " ");
            $('meta[name="twitter:description"]').remove();
            $(strtwitterdes).appendTo(document.head);

            $('meta[name="twitter:url"]').remove();
            $("head").append("<meta name='twitter:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:url"]').remove();
            $("head").append("<meta property='og:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:title"]').remove();
            $("head").append("<meta property='og:title' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " latest results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " financial results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " quarterly results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " annual results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " audited results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " unaudited results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Standalone results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Consolidated results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Segment wise Results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Income, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Revenue, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " PAT, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Profit after Tax, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Net Profit," + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " EPS, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Earnings per Share , BSE, BSEIndia'>");

            $('meta[property="og:description"]').remove();
            $("head").append("<meta property='og:description' content='" + "Quarterly & Annual Financial Results of  " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Check latest quarterly results and compare financial performance over past years. Get latest Standalone, Consolidated and Segment wise financial results.'>");
        }
        document.title = $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Financial Results – Quarterly & Annual, Quarterly Trends, Annual Trends |BSE"
    }

    $rootScope.$on('$includeContentLoaded', function (event, url) {
        //console.log(event);
        //console.log(url);
        if (url == '/GetQuote/stk_report_special.html') {
            $('#collapse2').removeClass("panel-collapse collapse");
            $('#collapse2').addClass("panel-collapse collapse in");
            $('#l61').removeClass("panel panel-active");
            $('#l61').addClass("list-group-item");
            var cls = $('#collapse2').attr('class');
            if (cls == 'panel-collapse collapse in') {
                $('#l61').removeClass("list-group-item");
                $('#l61').addClass("panel panel-active");
                $('#l61').parent().addClass("divpanel-ative");
                $('#collapse2').css('display', 'block');
            }
        }
    });


}]);
//Function for finacial Annual Reports
getquote.constant('serviceurl5', {
    url_annreport: 'AnnualReport_New/w'
});

getquote.controller('eqannreportController', ['serviceurl5', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqannreportController(serviceurl5, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {




    $scope.loader = {
        ARState: 'loading',
        ARdelay: false,
    };
    $scope.fn_annreport = function () {
        $scope.loader.ARState = 'loading';
        $scope.loader.ARdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl5.url_annreport;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode } }).then(function successCallback(response) {
            $scope.annreportData = response.data;
            $scope.loader.ARState = 'loaded';
            $scope.fn_reptannTitle($scope.annreportData.Table[0].year);
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.ARdelay = true;
                $scope.loader.ARState = 'loading';
            }
        });
    }

    $scope.fn_reptannTitle = function (y) {
        var strkeywords = "";
        var strDescp = "";
        var strRawUrl = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
        var strRawUrl1 = $location.absUrl().replace(/[\\#,+()$~%"*<>{};]/g, '_');
        var strArray = strRawUrl.split('/');
        if (strArray != null && strArray.length > 5) {
            strkeywords = "<meta name='keywords' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Latest Annual Report, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Annual Report " + y + ", " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Historical Annual Reports, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Annual Reports, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  Directors Report, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  Financial Report, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Balance Sheet, BSE, BSEIndia /'>";
            strkeywords = strkeywords.replace("-", " ");
            strDescp = "<meta name='description' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Annual Report " + y + ", " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Historical Annual Reports, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " all Annual Reports on BSE India.  '/>";
            strDescp = strDescp.replace("-", " ");
            $('meta[name=description]').remove();
            $('meta[name=keywords]').remove();
            $(strkeywords).appendTo(document.head);
            $(strDescp).appendTo(document.head);

            var strtwittertitle = "<meta name='twitter:title' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Latest Annual Report, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Annual Report " + y + ", " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Historical Annual Reports, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Annual Reports, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  Directors Report, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  Financial Report, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Balance Sheet, BSE, BSEIndia /'>";
            strtwittertitle = strtwittertitle.replace("-", " ");
            $('meta[name="twitter:title"]').remove();
            $(strtwittertitle).appendTo(document.head);

            var strtwitterdes = "<meta name='twitter:description' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Annual Report " + y + ", " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Historical Annual Reports, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " all Annual Reports on BSE India.  '/>";
            strtwitterdes = strtwitterdes.replace("-", " ");
            $('meta[name="twitter:description"]').remove();
            $(strtwitterdes).appendTo(document.head);

            $('meta[name="twitter:url"]').remove();
            $("head").append("<meta name='twitter:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:url"]').remove();
            $("head").append("<meta property='og:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:title"]').remove();
            $("head").append("<meta property='og:title' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Latest Annual Report, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Annual Report " + y + ", " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Historical Annual Reports, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Annual Reports, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  Directors Report, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  Financial Report, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Balance Sheet, BSE, BSEIndia /'>");

            $('meta[property="og:description"]').remove();
            $("head").append("<meta property='og:description' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Annual Report " + y + ", " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Historical Annual Reports, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " all Annual Reports on BSE India.  '/>");
        }
        document.title = $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Annual Reports " + y + ", " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Annual Reports | BSE ";
    }
    $rootScope.$on('$includeContentLoaded', function (event, url) {
        //console.log(event);
        //console.log(url);
        if (url == '/GetQuote/stk_annualreport.html') {
            $('#collapse2').removeClass("panel-collapse collapse");
            $('#collapse2').addClass("panel-collapse collapse in");
            $('#l62').removeClass("panel panel-active");
            $('#l62').addClass("list-group-item");
            var cls = $('#collapse2').attr('class');
            if (cls == 'panel-collapse collapse in') {
                $('#l62').removeClass("list-group-item");
                $('#l62').addClass("panel panel-active");
                $('#l62').parent().addClass("divpanel-ative");
                $('#collapse2').css('display', 'block');
            }
        }
    });
}]);
//Fuction for Additional Info
getquote.constant('serviceurl6', {
    url_InvitDetails: 'InvitDetails/w'
});

getquote.controller('eqaddinfoController', ['serviceurl16', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqaddinfoController(serviceurl6, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {





    $scope.loader = {
        loading: false,
        loaded: false,
    }
    $scope.fn_InvitDetails = function () {
        var url = mainapi.api_domainLIVE + serviceurl6.url_InvitDetails;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode } }).then(function successCallback(response) {
            $scope.InvitDetails = response.data;
            $scope.fn_AdinfTitle();
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
        });
    }
    $scope.fn_AdinfTitle = function () {
        var strkeywords = "";
        var strDescp = "";
        var strRawUrl = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
        var strRawUrl1 = $location.absUrl().replace(/[\\#,+()$~%"*<>{};]/g, '_');
        var strArray = strRawUrl.split('/');
        if (strArray != null && strArray.length > 5) {
            strkeywords = "<meta name='keywords' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " share price, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " share price, " + strArray[6] + " share price, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " live stock price, " + $rootScope.camelize(strArray[5].replace(" - ", " ").replace(" - ", " ")) + " live stock price,  " + strArray[6] + " live stock price, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " stock price today, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " stock price today,  " + strArray[6] + " live stock price, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " latest updates, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " news, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " quotes, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " graph,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " chart,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " 52 week high,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " 52 week low,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  market  capitalisation,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  buy price, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  buy quantity,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " sell price,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " sell quantity, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " bid , " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " offer, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " intraday price,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Net profit margin, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " EPS, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " PE, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Price Earnings, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " PB, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Price to Book Value, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " ROE, Return on Equity, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Industry, BSE, BSEIndia'>";
            strkeywords = strkeywords.replace("-", " ");
            strDescp = "<meta name='description' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Live BSE Share Price today, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " latest news,  " + strArray[6] + "  announcements. " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " financial results,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " shareholding, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " annual reports, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " pledge, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " insider trading and compare with peer companies.'>";
            strDescp = strDescp.replace("-", " ");
            $('meta[name=description]').remove();
            $('meta[name=keywords]').remove();
            $(strkeywords).appendTo(document.head);
            $(strDescp).appendTo(document.head);

            var strtwittertitle = "<meta name='twitter:title' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " share price, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " share price, " + strArray[6] + " share price, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " live stock price, " + $rootScope.camelize(strArray[5].replace(" - ", " ").replace(" - ", " ")) + " live stock price,  " + strArray[6] + " live stock price, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " stock price today, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " stock price today,  " + strArray[6] + " live stock price, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " latest updates, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " news, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " quotes, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " graph,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " chart,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " 52 week high,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " 52 week low,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  market  capitalisation,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  buy price, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  buy quantity,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " sell price,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " sell quantity, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " bid , " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " offer, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " intraday price,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Net profit margin, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " EPS, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " PE, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Price Earnings, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " PB, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Price to Book Value, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " ROE, Return on Equity, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Industry, BSE, BSEIndia'>";
            strtwittertitle = strtwittertitle.replace("-", " ");
            $('meta[name="twitter:title"]').remove();
            $(strtwittertitle).appendTo(document.head);

            var strtwitterdes = "<meta name='twitter:description' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Live BSE Share Price today, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " latest news,  " + strArray[6] + "  announcements. " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " financial results,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " shareholding, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " annual reports, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " pledge, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " insider trading and compare with peer companies.'>";
            strtwitterdes = strtwitterdes.replace("-", " ");
            $('meta[name="twitter:description"]').remove();
            $(strtwitterdes).appendTo(document.head);

            $('meta[name="twitter:url"]').remove();
            $("head").append("<meta name='twitter:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:url"]').remove();
            $("head").append("<meta property='og:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:title"]').remove();
            $("head").append("<meta property='og:title' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " share price, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " share price, " + strArray[6] + " share price, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " live stock price, " + $rootScope.camelize(strArray[5].replace(" - ", " ").replace(" - ", " ")) + " live stock price,  " + strArray[6] + " live stock price, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " stock price today, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " stock price today,  " + strArray[6] + " live stock price, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " latest updates, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " news, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " quotes, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " graph,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " chart,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " 52 week high,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " 52 week low,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  market  capitalisation,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  buy price, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  buy quantity,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " sell price,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " sell quantity, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " bid , " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " offer, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " intraday price,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Net profit margin, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " EPS, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " PE, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Price Earnings, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " PB, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Price to Book Value, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " ROE, Return on Equity, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Industry, BSE, BSEIndia'>");

            $('meta[property="og:description"]').remove();
            $("head").append("<meta property='og:description' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Live BSE Share Price today, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " latest news,  " + strArray[6] + "  announcements. " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " financial results,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " shareholding, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " annual reports, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " pledge, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " insider trading and compare with peer companies.'>");
        }
        document.title = $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Live Stock Price , " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Live Share Price, " + strArray[6] + " | BSE ";
    }
}]);
//Function for boardmeeting
getquote.constant('serviceurl7', {
    url_boardmting: 'BoardMeeting/w'
});

getquote.controller('eqboardmeetingController', ['serviceurl7', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqboardmeetingController(serviceurl7, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {


    $scope.loader = {
        BMState: 'loading',
        BMdelay: false,
    };

    $scope.loader = {
        loading: false,
        loaded: false,
    }

    $scope.fn_boardmting = function () {
        $scope.loader.BMState = 'loading';
        $scope.loader.BMdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl7.url_boardmting;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode } }).then(function successCallback(response) {
            $scope.BMData = response.data;
            $scope.loader.BMState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.BMdelay = true;
                $scope.loader.BMState = 'loading';
            }
        });
    }


    $scope.intervalFunction = function () {
        $timeout(function () {
            if (document.visibilityState == "visible") {
                $scope.fn_boardmting();
            }
            $scope.intervalFunction();
        }, 60000)
    };
    // Kick off the interval
    $scope.intervalFunction();

    $scope.recallFunction = function () {
        $timeout(function () {
            if ($scope.loader.BMdelay == true) { $scope.fn_boardmting(); }

            $scope.recallFunction();
        }, 20000)
    };
    $scope.recallFunction();

    $scope.fn_BOFMfTitle = function () {
        var strkeywords = "";
        var strDescp = "";
        var strRawUrl = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
        var strRawUrl1 = $location.absUrl().replace(/[\\#,+()$~%"*<>{};]/g, '_');
        var strArray = strRawUrl.split('/');
        if (strArray != null && strArray.length > 5) {
            strkeywords = "<meta name='keywords' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " board meeting, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " board meeting purpose, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " board meeting date,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " board meeting for Results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " board meeting for dividend, BSE, BSEIndia '/>";
            strkeywords = strkeywords.replace("-", " ");
            strDescp = "<meta name='description' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Board Meetings date and purpose of meeting, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Board Meetings  '/> ";
            strDescp = strDescp.replace("-", " ");
            $('meta[name=description]').remove();
            $('meta[name=keywords]').remove();
            $(strkeywords).appendTo(document.head);
            $(strDescp).appendTo(document.head);

            var strtwittertitle = "<meta name='twitter:title' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " board meeting, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " board meeting purpose, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " board meeting date,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " board meeting for Results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " board meeting for dividend, BSE, BSEIndia '/>";
            strtwittertitle = strtwittertitle.replace("-", " ");
            $('meta[name="twitter:title"]').remove();
            $(strtwittertitle).appendTo(document.head);

            var strtwitterdes = "<meta name='twitter:description' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Board Meetings date and purpose of meeting, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Board Meetings  '/> ";
            strtwitterdes = strtwitterdes.replace("-", " ");
            $('meta[name="twitter:description"]').remove();
            $(strtwitterdes).appendTo(document.head);


            $('meta[name="twitter:url"]').remove();
            $("head").append("<meta name='twitter:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:url"]').remove();
            $("head").append("<meta property='og:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:title"]').remove();
            $("head").append("<meta property='og:title' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " board meeting, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " board meeting purpose, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " board meeting date,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " board meeting for Results, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " board meeting for dividend, BSE, BSEIndia '/>");

            $('meta[property="og:description"]').remove();
            $("head").append("<meta property='og:description' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Board Meetings date and purpose of meeting, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Board Meetings  '/> ");

        }
        document.title = $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Board Meetings, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Board Meetings, |BSE ";
    }
    $scope.fn_BOFMfTitle();

    $rootScope.$on('$includeContentLoaded', function (event, url) {
        //console.log(event);
        //console.log(url);
        if (url == '/GetQuote/stk_boardmeeting.html') {
            $('#collapse3').removeClass("panel-collapse collapse");
            $('#collapse3').addClass("panel-collapse collapse in");
            $('#l71').removeClass("panel panel-active");
            $('#l71').addClass("list-group-item");
            var cls = $('#collapse3').attr('class');
            if (cls == 'panel-collapse collapse in') {
                $('#l71').removeClass("list-group-item");
                $('#l71').addClass("panel panel-active");
                $('#l71').parent().addClass("divpanel-ative");
                $('#collapse3').css('display', 'block');
            }
        }
    });
}]);
//Function for consolitedpledge
getquote.constant('serviceurl8', {
    url_ConPldge: "ConsolidatePledge/w",
    url_DwnldExcelsolidatepledge: "DwnldExcel_ConPldge/w"
});

getquote.controller('eqconsolidatepledgeController', ['serviceurl8', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqconsolidatepledgeController(serviceurl8, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {


    $scope.loader = {

        ConsoliState: 'loading',
        Consolidelay: false,
    };



    $scope.fn_ConPldge = function () {
        $scope.loader.ConsoliState = 'loading';
        $scope.loader.Consolidelay = false;
        var url = mainapi.api_domainLIVE + serviceurl8.url_ConPldge;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode } }).then(function successCallback(response) {
            $scope.ConPldge = response.data;
            $scope.loader.ConsoliState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.Consolidelay = true;
                $scope.loader.ConsoliState = 'loading';
            }
        });
    }

    $scope.fn_downloadexcel = function () {
        var url = mainapi.api_domainLIVE + serviceurl8.url_DwnldExcelsolidatepledge + "?scripcode=" + $scope.scripcode + "&flag=ConPldge";
        return url;

    }

    $rootScope.$on('$includeContentLoaded', function (event, url) {
        //console.log(event);
        //console.log(url);
        if (url == '/GetQuote/stk_consolitedpledge.html') {
            $('#collapse4').removeClass("panel-collapse collapse");
            $('#collapse4').addClass("panel-collapse collapse in");
            $('#l126').removeClass("panel panel-active");
            $('#l126').addClass("list-group-item");
            var cls = $('#collapse4').attr('class');
            if (cls == 'panel-collapse collapse in') {
                $('#l126').removeClass("list-group-item");
                $('#l126').addClass("panel panel-active");
                $('#l126').parent().addClass("divpanel-ative");
                $('#collapse4').css('display', 'block');
            }
        }
    });


    $scope.fn_consolidpledgeDataTitle = function () {
        var strkeywords = "";
        var strDescp = "";
        var strRawUrl = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
        var strRawUrl1 = $location.absUrl().replace(/[\\#,+()$~%"*<>{};]/g, '_');
        var strArray = strRawUrl.split('/');
        if (strArray != null && strArray.length > 5) {
            strkeywords = "<meta name='keywords' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Consolidated Pledge Data,BSE, BSEIndia'/>";
            strkeywords = strkeywords.replace("-", " ");
            strDescp = "<meta name='description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Consolidated Pledge Data '/> ";
            strDescp = strDescp.replace("-", " ");
            $('meta[name=description]').remove();
            $('meta[name=keywords]').remove();
            $(strkeywords).appendTo(document.head);
            $(strDescp).appendTo(document.head);

            var strtwittertitle = "<meta name='twitter:title' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Consolidated Pledge Data,BSE, BSEIndia'/>";
            strtwittertitle = strtwittertitle.replace("-", " ");
            $('meta[name="twitter:title"]').remove();
            $(strtwittertitle).appendTo(document.head);

            var strtwitterdes = "<meta name='twitter:description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Consolidated Pledge Data '/> ";
            strtwitterdes = strtwitterdes.replace("-", " ");
            $('meta[name="twitter:description"]').remove();
            $(strtwitterdes).appendTo(document.head);

            $('meta[name="twitter:url"]').remove();
            $("head").append("<meta name='twitter:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:url"]').remove();
            $("head").append("<meta property='og:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:title"]').remove();
            $("head").append("<meta property='og:title' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Consolidated Pledge Data,BSE, BSEIndia'/>");

            $('meta[property="og:description"]').remove();
            $("head").append("<meta property='og:description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Consolidated Pledge Data '/> ");
        }
        document.title = $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Consolidated Pledge Data |BSE ";
    }
    $scope.fn_consolidpledgeDataTitle();
}]);
//function for corpact
getquote.constant('serviceurl9', {
    url_CorpAction: 'CorporateAction/w'
});

getquote.controller('eqcorpactController', ['serviceurl9', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqcorpactController(serviceurl9, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {



    $scope.loader = {
        CAAState: 'loading',
        CAAdelay: false,
    };

    $scope.fn_CorpAction = function () {
        $scope.loader.CAAState = 'loading';
        $scope.loader.CAAdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl9.url_CorpAction;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode } }).then(function successCallback(response) {
            $scope.CorpAct = response.data;
            $scope.loader.CAAState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.CAAdelay = true;
                $scope.loader.CAAState = 'loading';
            }
        });
    }

    $scope.checknull = function (entnum) {
        if (entnum == null || entnum == undefined || entnum == "" || entnum == 0)
            return true;
        else
            return false;
    }

    $scope.fn_CorpTitle = function () {
        var strkeywords = "";
        var strDescp = "";
        var strRawUrl = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
        var strRawUrl1 = $location.absUrl().replace(/[\\#,+()$~%"*<>{};]/g, '_');
        var strArray = strRawUrl.split('/');
        if (strArray != null && strArray.length > 5) {

            strkeywords = "<meta name='keywords' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Corporate Actions, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Corporate Action Purpose, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Ex Date, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Record Date, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Book Closure Date, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " BC, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " RD, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " No Delivery Period, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " dividend announced, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " dividend," + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " interim dividend, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " final dividend, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " bonus issue, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " rights issue, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " stock splits, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " amalgamation, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " spin off, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " sub division of equity shares, BSE, BSEIndia '/>";
            strkeywords = strkeywords.replace("-", " ");
            strDescp = "<meta name='description' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + "  Corporate actions, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " forthcoming corporate actions such as dividend, interim dividend, right issues, stock split, buyback issues, bonus issues etc./'>";
            strDescp = strDescp.replace("-", " ");
            $('meta[name=description]').remove();
            $('meta[name=keywords]').remove();
            $(strkeywords).appendTo(document.head);
            $(strDescp).appendTo(document.head);

            var strtwittertitle = "<meta name='twitter:title' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Corporate Actions, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Corporate Action Purpose, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Ex Date, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Record Date, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Book Closure Date, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " BC, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " RD, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " No Delivery Period, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " dividend announced, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " dividend," + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " interim dividend, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " final dividend, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " bonus issue, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " rights issue, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " stock splits, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " amalgamation, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " spin off, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " sub division of equity shares, BSE, BSEIndia '/>";
            strtwittertitle = strtwittertitle.replace("-", " ");
            $('meta[name="twitter:title"]').remove();
            $(strtwittertitle).appendTo(document.head);

            var strtwitterdes = "<meta name='twitter:description' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + "  Corporate actions, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " forthcoming corporate actions such as dividend, interim dividend, right issues, stock split, buyback issues, bonus issues etc./'>";
            strtwitterdes = strtwitterdes.replace("-", " ");
            $('meta[name="twitter:description"]').remove();
            $(strtwitterdes).appendTo(document.head);

            $('meta[name="twitter:url"]').remove();
            $("head").append("<meta name='twitter:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:url"]').remove();
            $("head").append("<meta property='og:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:title"]').remove();
            $("head").append("<meta property='og:title' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Corporate Actions, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Corporate Action Purpose, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Ex Date, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Record Date, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Book Closure Date, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " BC, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " RD, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " No Delivery Period, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " dividend announced, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " dividend," + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " interim dividend, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " final dividend, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " bonus issue, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " rights issue, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " stock splits, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " amalgamation, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " spin off, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " sub division of equity shares, BSE, BSEIndia '/>");

            $('meta[property="og:description"]').remove();
            $("head").append("<meta property='og:description' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + "  Corporate actions, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " forthcoming corporate actions such as dividend, interim dividend, right issues, stock split, buyback issues, bonus issues etc./'>");
        }
        document.title = $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Corporate Actions, |BSE";
    }
    $scope.fn_CorpTitle();
}]);

//Function for peergroup
getquote.constant('serviceurl10', {
    url_PeerGpComp: 'PeerGpCom/w',
    url_CompPeer: 'ComparePeer/w',
    url_Quotes: 'PeerSmartSearch/w'
});

getquote.controller('eqpeergroupController', ['serviceurl10', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqpeergroupController(serviceurl10, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {



    $scope.loader = {
        loading: false,
        loaded: false,
    }

    $scope.scriptocompare = [];
    $scope.inputtxt = "";
    $scope.View = "in Cr.";
    $scope.Viewin = "View in (Million)";

    $scope.GetQuoteTable2 = function (event) {
        if (event.keyCode != 40 && event.keyCode != 38 && event.keyCode != 13) {
            if ($scope.inputtext != "" && $scope.inputtext.length > 1) {
                var url = mainapi.api_domainLIVE + serviceurl10.url_Quotes + "?Type=EQ&text=" + $scope.inputtext;
                $http.get(url).then(function successCallback(response) {
                    $scope.SearchQuote2 = response.data;
                    $('#ulSearchQuote2').css({ "display": "block" });

                }, function errorCallback(response) {
                    $scope.status = response.status + "_" + response.statusText;
                });
            }
            else {
                $scope.SearchQuote2 = "";
                $('#ulSearchQuote2').css({ "display": "none" });
            }
        }
    };

    $scope.fn_CompPeer = function () {
        $scope.inputtxt = "";
        var url = mainapi.api_domainLIVE + serviceurl10.url_CompPeer;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, scripcomare: $scope.scriptocompare.join() } }).then(function successCallback(response) {
            $scope.CompPeer = response.data;
            $scope.scriptocompare = [];
            for (var i = 0; i < $scope.CompPeer.Table.length; i++) {
                if ($scope.CompPeer.Table[i].Checked) {
                    $scope.scriptocompare.push($scope.CompPeer.Table[i].scrip_cd);
                }
            }
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
        });
    }

    $scope.fn_PeerGrp = function () {
        var selectedscripts = $('input[name=scripchkbxlist]:checked');
        $scope.scriptocompare = [];
        if (selectedscripts != undefined) {
            for (var i = 0; i < selectedscripts.length; i++) {
                $scope.scriptocompare.push(selectedscripts[i].value);
            }
        }
        var url = mainapi.api_domainLIVE + serviceurl10.url_PeerGpComp;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, scripcomare: $scope.scriptocompare.join() } }).then(function successCallback(response) {
            $scope.PeerGpComp = response.data;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
        });
    }
    $scope.fn_Viewin = function () {
        if ($scope.View == "in Cr.") {
            $scope.Viewin = "View in (Cr.)";
            $scope.View = "in Million";
            for (var i = 0; i < $scope.PeerGpComp.Table.length; i++) {
                if (!$scope.checknull($scope.PeerGpComp.Table[i].Revenue))
                    $scope.PeerGpComp.Table[i].Revenue = $scope.PeerGpComp.Table[i].Revenue * 10;
                if (!$scope.checknull($scope.PeerGpComp.Table[i].PAT))
                    $scope.PeerGpComp.Table[i].PAT = $scope.PeerGpComp.Table[i].PAT * 10;
                if (!$scope.checknull($scope.PeerGpComp.Table[i].Equity))
                    $scope.PeerGpComp.Table[i].Equity = $scope.PeerGpComp.Table[i].Equity * 10;
            }
            for (var i = 0; i < $scope.PeerGpComp.Table1.length; i++) {
                if (!$scope.checknull($scope.PeerGpComp.Table1[i].Revenue))
                    $scope.PeerGpComp.Table1[i].Revenue = $scope.PeerGpComp.Table1[i].Revenue * 10;
                if (!$scope.checknull($scope.PeerGpComp.Table1[i].PAT))
                    $scope.PeerGpComp.Table1[i].PAT = $scope.PeerGpComp.Table1[i].PAT * 10;
                if (!$scope.checknull($scope.PeerGpComp.Table1[i].Equity))
                    $scope.PeerGpComp.Table1[i].Equity = $scope.PeerGpComp.Table1[i].Equity * 10;
            }
        }
        else if ($scope.View == "in Million") {
            $scope.Viewin = "View in (Million)";
            $scope.View = "in Cr.";
            for (var i = 0; i < $scope.PeerGpComp.Table.length; i++) {
                if (!$scope.checknull($scope.PeerGpComp.Table[i].Revenue))
                    $scope.PeerGpComp.Table[i].Revenue = $scope.PeerGpComp.Table[i].Revenue / 10;
                if (!$scope.checknull($scope.PeerGpComp.Table[i].PAT))
                    $scope.PeerGpComp.Table[i].PAT = $scope.PeerGpComp.Table[i].PAT / 10;
                if (!$scope.checknull($scope.PeerGpComp.Table[i].Equity))
                    $scope.PeerGpComp.Table[i].Equity = $scope.PeerGpComp.Table[i].Equity / 10;
            }
            for (var i = 0; i < $scope.PeerGpComp.Table1.length; i++) {
                if (!$scope.checknull($scope.PeerGpComp.Table1[i].Revenue))
                    $scope.PeerGpComp.Table1[i].Revenue = $scope.PeerGpComp.Table1[i].Revenue / 10;
                if (!$scope.checknull($scope.PeerGpComp.Table1[i].PAT))
                    $scope.PeerGpComp.Table1[i].PAT = $scope.PeerGpComp.Table1[i].PAT / 10;
                if (!$scope.checknull($scope.PeerGpComp.Table1[i].Equity))
                    $scope.PeerGpComp.Table1[i].Equity = $scope.PeerGpComp.Table1[i].Equity / 10;
            }
        }
    }
    $scope.trustAsHtml = function (string) {
        return $sce.trustAsHtml(string);
    };
    $scope.getNumber = function (num) {
        return new Array(num);
    }
    $scope.checknull = function (entnum) {
        if (entnum == null || entnum == undefined || entnum == "" || entnum == 0)
            return true;
        else
            return false;
    }
    $scope.fnPeerTab = function (tabindex) {
        $scope.tab = tabindex;
        $("#aqr").attr("aria-expanded", !1);
        $("#aanualtrd").attr("aria-expanded", !1);
        $("#abonus").attr("aria-expanded", !1);
        if ($scope.tab == "qtly") {
            $("#aqr").attr("aria-expanded", !0);
        }
        if ($scope.tab == "ann") {
            $("#aanualtrd").attr("aria-expanded", !0);
        }
        if ($scope.tab == "bnd") {
            $("#abonus").attr("aria-expanded", !0);
        }
    }

    $scope.fn_peerGrpTitle = function () {
        var strkeywords = "";
        var strDescp = "";
        var strRawUrl = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
        var strRawUrl1 = $location.absUrl().replace(/[\\#,+()$~%"*<>{};]/g, '_');
        var strArray = strRawUrl.split('/');
        if (strArray != null && strArray.length > 5) {
            strkeywords = "<meta name='keywords' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Peer Group Companies, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Peer Group Companies Information " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Peer Group Companies Financials Comparison, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Peer Group Companies Share Price, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Peer Group Companies Ownership Comparison, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Peer Group Companies Dividend Comparison, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Peer Group Companies Bonus Comparison, BSE, BSEIndia'/>";
            strkeywords = strkeywords.replace("-", " ");
            strDescp = "<meta name='description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Peer Group Companies Information - Quarterly Trends, Annual Trends, Bonus and Dividends, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Peer Group Companies Comparison - Quarterly Trends, Annual Trends, Bonus and Dividends '/>";
            strDescp = strDescp.replace("-", " ");
            $('meta[name=description]').remove();
            $('meta[name=keywords]').remove();
            $(strkeywords).appendTo(document.head);
            $(strDescp).appendTo(document.head);

            var strtwittertitle = "<meta name='twitter:title' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Peer Group Companies, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Peer Group Companies Information " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Peer Group Companies Financials Comparison, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Peer Group Companies Share Price, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Peer Group Companies Ownership Comparison, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Peer Group Companies Dividend Comparison, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Peer Group Companies Bonus Comparison, BSE, BSEIndia'/>";
            strtwittertitle = strtwittertitle.replace("-", " ");
            $('meta[name="twitter:title"]').remove();
            $(strtwittertitle).appendTo(document.head);

            var strtwitterdes = "<meta name='twitter:description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Peer Group Companies Information - Quarterly Trends, Annual Trends, Bonus and Dividends, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Peer Group Companies Comparison - Quarterly Trends, Annual Trends, Bonus and Dividends '/>";
            strtwitterdes = strtwitterdes.replace("-", " ");
            $('meta[name="twitter:description"]').remove();
            $(strtwitterdes).appendTo(document.head);

            $('meta[name="twitter:url"]').remove();
            $("head").append("<meta name='twitter:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:url"]').remove();
            $("head").append("<meta property='og:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:title"]').remove();
            $("head").append("<meta property='og:title' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Peer Group Companies, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Peer Group Companies Information " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Peer Group Companies Financials Comparison, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Peer Group Companies Share Price, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Peer Group Companies Ownership Comparison, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Peer Group Companies Dividend Comparison, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Peer Group Companies Bonus Comparison, BSE, BSEIndia'/>");

            $('meta[property="og:description"]').remove();
            $("head").append("<meta property='og:description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Peer Group Companies Information - Quarterly Trends, Annual Trends, Bonus and Dividends, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Peer Group Companies Comparison - Quarterly Trends, Annual Trends, Bonus and Dividends '/>");
        }
        document.title = $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Peer Group Companies Quarterly Trends, Annual Trends, Bonus and Dividends |BSE ";
    }
    $scope.fn_peerGrpTitle();
}]);

//Function for promoter/nonpromoter/pleged
getquote.constant('serviceurl11', {
    url_sddsastprmt: "sddsastPM/w",
    url_sddsastnonprmt: "sddsastPM/w",
    url_sddpledge: "sddpledge/w",
    url_DwnldExcelprmt: "SDDSastPromNonPromCSV/w",
    url_DwnldExcelnonprmt: "SDDSastPromNonPromCSV/w",
    url_DwnldExcelplege: "SDDSastPledgeCSV/w",
    url_Dwnldpdf: "PledgeSddRegulationDownload/w"
})

getquote.controller('eqsddsastprmtController', ['serviceurl11', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqsddsastprmtController(serviceurl11, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {




    $scope.loader = {

        ISState: 'loading',
        ISdelay: false,
    };
    $scope.FromDate = '';
    $scope.ToDate = '';

    $scope.viewby = 25;
    $scope.totalItems = 0;
    $scope.currentPage = 1;
    $scope.itemsPerPage = $scope.viewby;
    $scope.maxSize = 5; //Number of pager buttons to show

    $scope.fn_sddsastprmt = function () {
        $scope.loader.ISState = 'loading';
        $scope.loader.ISdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl11.url_sddsastprmt;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, FDate: $scope.FromDate, TDate: $scope.ToDate, Flag: 0 } }).then(function successCallback(response) {
            $scope.sddsastprmt = response.data;
            $scope.loader.ISState = 'loaded';
            $scope.totalItems = $scope.sddsastprmt.Table.length;
            $scope.currentPage = 1;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.ISdelay = true;
                $scope.loader.ISState = 'loading';
            }
        });
    }

    $scope.fn_submit_prmt = function () {
        if ($scope.FromDate != "" && $scope.ToDate != "") {
            var fmdt = new Date($scope.FromDate.split('/')[2], $scope.FromDate.split('/')[1] - 1, $scope.FromDate.split('/')[0]);
            var todt = new Date($scope.ToDate.split('/')[2], $scope.ToDate.split('/')[1] - 1, $scope.ToDate.split('/')[0]);
            if (fmdt > todt) {
                alert('From date should be less than To date'); return;
            }
            else {
                $scope.fn_sddsastprmt();
            }
        }
        else if ($scope.ToDate != "" && $scope.FromDate == "") {
            alert('Please enter From Date');
        }
        else if ($scope.ToDate == "" && $scope.FromDate != "") {
            alert('Please enter To Date');
        }
        else if ($scope.ToDate == "" && $scope.FromDate == "") {
            alert('Please enter From and To Date');
        }
    }
    $scope.fn_downloadexcelprmt = function () {
        var url = mainapi.api_domainLIVE + serviceurl11.url_DwnldExcelprmt + "?scripcode=" + $scope.scripcode + "&FDate=" + $scope.FromDate + "&TDate=" + $scope.ToDate + "&Flag=0";
        return url;
    }

    $scope.fn_sddsastnonprmt = function () {
        $scope.loader.ISState = 'loading';
        $scope.loader.ISdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl11.url_sddsastnonprmt;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, FDate: $scope.FromDate, TDate: $scope.ToDate, Flag: 1 } }).then(function successCallback(response) {
            $scope.sddsastnonprmt = response.data;
            $scope.loader.ISState = 'loaded';
            $scope.totalItems = $scope.sddsastnonprmt.Table.length;
            $scope.currentPage = 1;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.ISdelay = true;
                $scope.loader.ISState = 'loading';
            }
        });
    }


    $scope.fn_submit_nonprmt = function () {
        if ($scope.FromDate != "" && $scope.ToDate != "") {
            var fmdt = new Date($scope.FromDate.split('/')[2], $scope.FromDate.split('/')[1] - 1, $scope.FromDate.split('/')[0]);
            var todt = new Date($scope.ToDate.split('/')[2], $scope.ToDate.split('/')[1] - 1, $scope.ToDate.split('/')[0]);
            if (fmdt > todt) {
                alert('From date should be less than To date'); return;
            }
            else {
                $scope.fn_sddsastnonprmt();
            }
        }
        else if ($scope.ToDate != "" && $scope.FromDate == "") {
            alert('Please enter From Date');
        }
        else if ($scope.ToDate == "" && $scope.FromDate != "") {
            alert('Please enter To Date');
        }
        else if ($scope.ToDate == "" && $scope.FromDate == "") {
            alert('Please enter From and To Date');
        }
    }

    $scope.fn_downloadexcelnonprmt = function () {
        var url = mainapi.api_domainLIVE + serviceurl11.url_DwnldExcelplege + "?scripcode=" + $scope.scripcode + "&FDate=" + $scope.FromDate + "&TDate=" + $scope.ToDate + "&Flag=1";
        return url;
    }

    $scope.fn_sddsastpleg = function () {
        $scope.loader.ISState = 'loading';
        $scope.loader.ISdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl11.url_sddpledge;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, FDate: $scope.FromDate, TDate: $scope.ToDate } }).then(function successCallback(response) {
            $scope.sddpledge = response.data;
            $scope.loader.ISState = 'loaded';
            $scope.totalItems = $scope.sddpledge.Table.length;
            $scope.currentPage = 1;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.ISdelay = true;
                $scope.loader.ISState = 'loading';
            }
        });
    }

    $scope.fn_submit_plege = function () {
        if ($scope.FromDate != "" && $scope.ToDate != "") {
            var fmdt = new Date($scope.FromDate.split('/')[2], $scope.FromDate.split('/')[1] - 1, $scope.FromDate.split('/')[0]);
            var todt = new Date($scope.ToDate.split('/')[2], $scope.ToDate.split('/')[1] - 1, $scope.ToDate.split('/')[0]);
            if (fmdt > todt) {
                alert('From date should be less than To date'); return;
            }
            else {
                $scope.fn_sddsastpleg();
            }
        }
        else if ($scope.ToDate != "" && $scope.FromDate == "") {
            alert('Please enter From Date');
        }
        else if ($scope.ToDate == "" && $scope.FromDate != "") {
            alert('Please enter To Date');
        }
        else if ($scope.ToDate == "" && $scope.FromDate == "") {
            alert('Please enter From and To Date');
        }
    }
    $scope.fn_downloadexcelplege = function () {
        var url = mainapi.api_domainLIVE + serviceurl11.url_DwnldExcelplege + "?scripcode=" + $scope.scripcode + "&FDate=" + $scope.FromDate + "&TDate=" + $scope.ToDate;
        return url;
    }

    $scope.fn_downloadpdf = function (Reg, ID) {
        $scope.Reg = Reg;
        $scope.ID = ID;
        var url = mainapi.api_domainLIVE + serviceurl11.url_Dwnldpdf + "?scripcode=" + $scope.scripcode + "&Reg=" + $scope.Reg + "&Id=" + $scope.ID;
        return url;
    }

    $rootScope.$on('$includeContentLoaded', function (event, url) {
        //console.log(event);
        // console.log(url);
        if (url == '/GetQuote/stk_sdd_sastnonpromoter.html') {
            $('#collapse4').removeClass("panel-collapse collapse");
            $('#collapse4').addClass("panel-collapse collapse in");
            $('#l121').removeClass("panel panel-active");
            $('#l121').addClass("list-group-item");
            var cls = $('#collapse4').attr('class');
            if (cls == 'panel-collapse collapse in') {
                $('#l121').removeClass("list-group-item");
                $('#l121').addClass("panel panel-active");
                $('#l121').parent().addClass("divpanel-ative");
                $('#collapse4').css('display', 'block');
            }
        }
        else if (url == '/GetQuote/stk_sdd_sastpromoter.html') {
            $('#collapse4').removeClass("panel-collapse collapse");
            $('#collapse4').addClass("panel-collapse collapse in");
            $('#l121').removeClass("panel panel-active");
            $('#l121').addClass("list-group-item");
            var cls = $('#collapse4').attr('class');
            if (cls == 'panel-collapse collapse in') {
                $('#l121').removeClass("list-group-item");
                $('#l121').addClass("panel panel-active");
                $('#l121').parent().addClass("divpanel-ative");
                $('#collapse4').css('display', 'block');
            }
        }
        else if (url == '/GetQuote/stk_sdd_sastpledge.html') {
            $('#collapse4').removeClass("panel-collapse collapse");
            $('#collapse4').addClass("panel-collapse collapse in");
            $('#l121').removeClass("panel panel-active");
            $('#l121').addClass("list-group-item");
            var cls = $('#collapse4').attr('class');
            if (cls == 'panel-collapse collapse in') {
                $('#l121').removeClass("list-group-item");
                $('#l121').addClass("panel panel-active");
                $('#l121').parent().addClass("divpanel-ative");
                $('#collapse4').css('display', 'block');
            }
        }
    });

}]);

//Function for insidertrade15
getquote.constant('serviceurl12', {
    url_InsiderTrd15: "InsiderTrade15/w",
    url_DwnldExcel15: "DwnldExcelIT15/w"
})

getquote.controller('eqinstrade15Controller', ['serviceurl12', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqinstrade15Controller(serviceurl12, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {





    $scope.loader = {

        ISState: 'loading',
        ISdelay: false,
    };
    $scope.FromDate = '';//null;
    $scope.ToDate = '';//null;
    //$scope.Fromindex = 0;
    //$scope.RecPerPage = 25;
    //$scope.TotalRecs = 0;
    $scope.viewby = 25;
    $scope.totalItems = 0;
    $scope.currentPage = 1;
    $scope.pagenumber = 0;
    $scope.loader.prevDisp = true;
    $scope.loader.NextDisp = true;
    $scope.itemsPerPage = $scope.viewby;
    $scope.maxSize = 5; //Number of pager buttons to show

    $scope.fn_PrevPage = function () {

        if ($scope.currentPage == 1) {
            $('#idprev').hide();
        }
        else if ($scope.currentPage != 1) {
            $scope.currentPage = $scope.currentPage - 1;
            $scope.fn_InsiderTrd15($scope.currentPage);
        }
    }
    $scope.fn_NextPage = function () {
        if ($scope.currentPage < $scope.pagenumber) {
            $scope.currentPage = $scope.currentPage + 1;
            $scope.fn_InsiderTrd15($scope.currentPage);
        }

        if ($scope.currentPage == $scope.pagenumber) {
            $('#idnext').hide();
            $scope.loader.NextDisp = false;
        }
    }

    $scope.fn_InsiderTrd15 = function (Pagenoa) {
        $scope.loader.ISState = 'loading';
        $scope.loader.ISdelay = false;
        $scope.currentPage1 = Pagenoa;
        var url = mainapi.api_domainLIVE + serviceurl12.url_InsiderTrd15;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, fromdt: $scope.FromDate, todt: $scope.ToDate, pageno: $scope.currentPage1 } }).then(function successCallback(response) {
            $scope.InsiderTrade = response.data;
            $scope.loader.ISState = 'loaded';
            $scope.totalItems = $scope.InsiderTrade.Table.length;
            //$scope.apply_pagination();
            //$scope.TotalRecs = $scope.InsiderTrade.Table.length;
            //var x = document.getElementsByTagName("PAGING");
            //x[0].attributes[2].value = '"' + $scope.TotalRecs + '"';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.ISdelay = true;
                $scope.loader.ISState = 'loading';
            }
        });
        if ($scope.totalItems <= 25) {
            $scope.pagenumber = 1;
            $scope.loader.NextDisp = false;
            $scope.loader.prevDisp = false;
        }
        else {
            $scope.pagenumber = Math.ceil($scope.totalItems / 25);

            //if ($scope.currentPage >= $scope.pagenumber && $scope.pagenumber!=1) { 

            if ($scope.currentPage == $scope.pagenumber) { $scope.loader.NextDisp = false }

            else if ($scope.currentPage < $scope.pagenumber) { $scope.loader.NextDisp = true; }
            else {
                $scope.loader.NextDisp = true;
                $scope.loader.prevDisp = true;
            }
        }
    }

    $scope.fn_InsiderTrd15filter = function (fromdt, todt) {
        $scope.loader.ISState = 'loading';
        $scope.loader.ISdelay = false;
        $scope.currentPage = 1;
        $scope.pagenumber = 0;
        var url = mainapi.api_domainLIVE + serviceurl12.url_InsiderTrd15;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, fromdt: $scope.FromDate, todt: $scope.ToDate, pageno: $scope.currentPage1 } }).then(function successCallback(response) {
            $scope.InsiderTrade = response.data;
            $scope.loader.ISState = 'loaded';
            $scope.totalItems = $scope.InsiderTrade.Table.length;
            if ($scope.totalItems <= 25) {
                $scope.pagenumber = 1;
                $scope.loader.NextDisp = false;
                $scope.loader.prevDisp = false;
            }
            else {
                $scope.pagenumber = Math.ceil($scope.totalItems / 25);

                //if ($scope.currentPage >= $scope.pagenumber && $scope.pagenumber!=1) { 

                if ($scope.currentPage == $scope.pagenumber) { $scope.loader.NextDisp = false }

                else if ($scope.currentPage < $scope.pagenumber) { $scope.loader.NextDisp = true; }
                else {
                    $scope.loader.NextDisp = true;
                    $scope.loader.prevDisp = true;
                }
            }

        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.ISdelay = true;
                $scope.loader.ISState = 'loading';
            }
        });

    }

    $scope.fn_submit_15 = function () {
        if ($scope.FromDate != "" && $scope.ToDate != "") {
            var fmdt = new Date($scope.FromDate.split('/')[2], $scope.FromDate.split('/')[1] - 1, $scope.FromDate.split('/')[0]);
            var todt = new Date($scope.ToDate.split('/')[2], $scope.ToDate.split('/')[1] - 1, $scope.ToDate.split('/')[0]);
            const oneDay = 24 * 60 * 60 * 1000; // hours*minutes*seconds*milliseconds
            const firstDate = new Date(fmdt);
            const secondDate = new Date(todt);
            const diffDays = Math.round(Math.abs((firstDate - secondDate) / oneDay));
            if (fmdt > todt) {
                alert('From date should be less than To date'); return false;
            } else if (diffDays > 92) {
                alert('Period should not be more than 3 month'); return false;
            }
            else {
                $scope.fn_InsiderTrd15filter($scope.FromDate, $scope.ToDate);
            }
        }
        else if ($scope.FromDate != "" && $scope.ToDate == "") {
            alert('Please enter From Date');
        }
        else if ($scope.FromDate == "" && $scope.ToDate != "") {
            alert('Please enter To Date');
        }
    }

    $scope.fn_downloadexcel = function () {
        var url = mainapi.api_domainLIVE + serviceurl12.url_DwnldExcel15 + "?scripcode=" + $scope.scripcode + "&fromdt=" + $scope.FromDate + "&todt=" + $scope.ToDate + "&flag=InsiderTrade15";
        return url;
        //$http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, fromdt: $scope.FromDate, todt: $scope.ToDate, flag: 'InsiderTrade15' } }).then(function successCallback(response) {

        //}, function errorCallback(response) {
        //    $scope.status = response.status + "_" + response.statusText;
        //});
    }

    $scope.fn_insider2015Title = function () {
        var strkeywords = "";
        var strDescp = "";
        var strRawUrl = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
        var strRawUrl1 = $location.absUrl().replace(/[\\#,+()$~%"*<>{};]/g, '_');
        var strArray = strRawUrl.split('/');
        if (strArray != null && strArray.length > 5) {
            strkeywords = "<meta name='keywords' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Insider Trading, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Insider Trades, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Insider Trading, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Insider Trades, SEBI Prohibition of Insider Trading Regulations 2015, BSE, BSEIndia'/>";
            strkeywords = strkeywords.replace("-", " ");
            strDescp = "<meta name='description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Insider Trading 2015  '/>";
            strDescp = strDescp.replace("-", " ");
            $('meta[name=description]').remove();
            $('meta[name=keywords]').remove();
            $(strkeywords).appendTo(document.head);
            $(strDescp).appendTo(document.head);

            var strtwittertitle = "<meta name='twitter:title' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Insider Trading, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Insider Trades, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Insider Trading, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Insider Trades, SEBI Prohibition of Insider Trading Regulations 2015, BSE, BSEIndia'/>";
            strtwittertitle = strtwittertitle.replace("-", " ");
            $('meta[name="twitter:title"]').remove();
            $(strtwittertitle).appendTo(document.head);

            var strtwitterdes = "<meta name='twitter:description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Insider Trading 2015  '/>";
            strtwitterdes = strtwitterdes.replace("-", " ");
            $('meta[name="twitter:description"]').remove();
            $(strtwitterdes).appendTo(document.head);

            $('meta[name="twitter:url"]').remove();
            $("head").append("<meta name='twitter:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:url"]').remove();
            $("head").append("<meta property='og:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:title"]').remove();
            $("head").append("<meta property='og:title' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Insider Trading, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Insider Trades, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Insider Trading, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Insider Trades, SEBI Prohibition of Insider Trading Regulations 2015, BSE, BSEIndia'/>");

            $('meta[property="og:description"]').remove();
            $("head").append("<meta property='og:description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Insider Trading 2015  '/>");
        }
        document.title = $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Insider Trading 2015 |BSE ";
    }
    $scope.fn_insider2015Title();

    $rootScope.$on('$includeContentLoaded', function (event, url) {
        //console.log(event);
        // console.log(url);
        if (url == '/GetQuote/stk_insidertrade15.html') {
            $('#collapse4').removeClass("panel-collapse collapse");
            $('#collapse4').addClass("panel-collapse collapse in");
            $('#l121').removeClass("panel panel-active");
            $('#l121').addClass("list-group-item");
            var cls = $('#collapse4').attr('class');
            if (cls == 'panel-collapse collapse in') {
                $('#l121').removeClass("list-group-item");
                $('#l121').addClass("panel panel-active");
                $('#l121').parent().addClass("divpanel-ative");
                $('#collapse4').css('display', 'block');
            }
        }
    });

    //$scope.filltbldata = function (page, pageSize) {
    //    $scope.Fromindex = page * pageSize;
    //}

    //$scope.apply_pagination = function () {
    //    var pagination = $('#pagination')
    //    pagination.twbsPagination({
    //        totalPages: Math.ceil($scope.InsiderTrade.Table.length / $scope.RecPerPage),
    //        visiblePages: 10,
    //        pageVariable:$scope.Fromindex,
    //        onPageClick: function (event, page) {
    //            //$scope.$apply(function () { $scope.Fromindex = Math.max(page - 1, 0) * $scope.RecPerPage; });//recPerPage;
    //            $scope.Fromindex = Math.max(page - 1, 0) * $scope.RecPerPage;
    //        }
    //    });
    //}

    //$scope.$watch('Fromindex', function () { console.log($scope.Fromindex); });


}]);
//Function for insidertrade92
getquote.constant('serviceurl13', {
    url_InsiderTrd92: "InsiderTrade92/w",
    url_DwnldExcel92: "DwnldExcelIT92/w"
})

getquote.controller('eqinstrade92Controller', ['serviceurl13', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqinstrade92Controller(serviceurl13, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {


    $scope.loader = {

        IS92State: 'loading',
        IS92delay: false,
    };


    $scope.loader = {
        loading: false,
        loaded: false,
    }

    $scope.linkfmdt = new Date(Date.now());
    $scope.linkendt = new Date(Date.now());
    $scope.linkendt.setDate($scope.linkendt.getDate() - 6);
    $scope.FromDate = '';
    $scope.ToDate = '';
    $scope.viewby = 25;
    $scope.totalItems = 0;
    $scope.currentPage = 1;
    $scope.itemsPerPage = $scope.viewby;
    $scope.maxSize = 5; //Number of pager buttons to show

    $scope.fn_InsiderTrd92 = function () {
        $scope.loader.IS92State = 'loading';
        $scope.loader.IS92delay = false;
        var url = mainapi.api_domainLIVE + serviceurl13.url_InsiderTrd92;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, fromdt: $scope.FromDate, todt: $scope.ToDate } }).then(function successCallback(response) {
            $scope.InsiderTrade = response.data;
            $scope.loader.IS92State = 'loaded';
            $scope.totalItems = $scope.InsiderTrade.Table.length;
            $scope.currentPage = 1;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.IS92delay = true;
                $scope.loader.IS92State = 'loading';
            }
        });
    }

    $scope.fn_submit_92 = function () {
        if ($scope.FromDate != "" && $scope.ToDate != "") {
            var fmdt = new Date($scope.FromDate.split('/')[2], $scope.FromDate.split('/')[1] - 1, $scope.FromDate.split('/')[0]);
            var todt = new Date($scope.ToDate.split('/')[2], $scope.ToDate.split('/')[1] - 1, $scope.ToDate.split('/')[0]);
            if (fmdt > todt) {
                alert('From date should be less than To date'); return;
            }
            else {
                $scope.fn_InsiderTrd92();
            }
        }
        else if ($scope.FromDate != "" && $scope.ToDate == "") {
            alert('Please enter From Date');
        }
        else if ($scope.FromDate == "" && $scope.ToDate != "") {
            alert('Please enter To Date');
        }
    }

    $scope.fn_downloadexcel = function () {
        var url = mainapi.api_domainLIVE + serviceurl13.url_DwnldExcel92 + "?scripcode=" + $scope.scripcode + "&fromdt=" + $scope.FromDate + "&todt=" + $scope.ToDate + "&flag=InsiderTrade92";
        return url;
        //$http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, fromdt: $scope.FromDate, todt: $scope.ToDate, flag: 'InsiderTrade15' } }).then(function successCallback(response) {

        //}, function errorCallback(response) {
        //    $scope.status = response.status + "_" + response.statusText;
        //});
    }

    $rootScope.$on('$includeContentLoaded', function (event, url) {
        if (url == '/GetQuote/stk_insidertrade92.html') {
            $('#collapse4').removeClass("panel-collapse collapse");
            $('#collapse4').addClass("panel-collapse collapse in");
            $('#l122').removeClass("panel panel-active");
            $('#l122').addClass("list-group-item");
            var cls = $('#collapse4').attr('class');
            if (cls == 'panel-collapse collapse in') {
                $('#l122').removeClass("list-group-item");
                $('#l122').addClass("panel panel-active");
                $('#l122').parent().addClass("divpanel-ative");
                $('#collapse4').css('display', 'block');
            }
        }
    });

    $scope.fn_insider1992Title = function () {
        var strkeywords = "";
        var strDescp = "";
        var strRawUrl = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
        var strRawUrl1 = $location.absUrl().replace(/[\\#,+()$~%"*<>{};]/g, '_');
        var strArray = strRawUrl.split('/');
        if (strArray != null && strArray.length > 5) {

            strkeywords = "<meta name='keywords' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Insider Trading " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Insider Trades, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Insider Trading, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Insider Trades, BSE, BSEIndia'/>";
            strkeywords = strkeywords.replace("-", " ");
            strDescp = "<meta name='description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Insider Trading 1992 '/>";
            strDescp = strDescp.replace("-", " ");
            $('meta[name=description]').remove();
            $('meta[name=keywords]').remove();
            $(strkeywords).appendTo(document.head);
            $(strDescp).appendTo(document.head);

            var strtwittertitle = "<meta name='twitter:title' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Insider Trading " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Insider Trades, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Insider Trading, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Insider Trades, BSE, BSEIndia'/>";
            strtwittertitle = strtwittertitle.replace("-", " ");
            $('meta[name="twitter:title"]').remove();
            $(strtwittertitle).appendTo(document.head);

            var strtwitterdes = "<meta name='twitter:description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Insider Trading 1992 '/>";
            strtwitterdes = strtwitterdes.replace("-", " ");
            $('meta[name="twitter:description"]').remove();
            $(strtwitterdes).appendTo(document.head);

            $('meta[name="twitter:url"]').remove();
            $("head").append("<meta name='twitter:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:url"]').remove();
            $("head").append("<meta property='og:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:title"]').remove();
            $("head").append("<meta property='og:title' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Insider Trading " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Insider Trades, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Insider Trading, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Insider Trades, BSE, BSEIndia'/>");

            $('meta[property="og:description"]').remove();
            $("head").append("<meta property='og:description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Insider Trading 1992 '/>");
        }
        document.title = $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Insider Trading 1992 |BSE ";
    }
    $scope.fn_insider1992Title();
}]);

//Function for shareholding search
getquote.constant('serviceurl14', {
    url_Sharehld_SHPQuarter: 'SHPQNewFormat/w',
    url_Shareddl: 'ShaDropdowndata/w',
    url_Sharehld: 'ShareHolding/w'
});
getquote.controller('shrhldController', ['serviceurl14', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function shrhldController(serviceurl14, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {



    $scope.loader = {
        SHState: 'loading',
        SHdelay: false,
    };

    var querystr = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
    var flag;
    var scripcode;
    var type;
    var qtrid;
    $scope.getUrlParameter = function (param, dummyPath) {
        var sPageURL = dummyPath || window.location.search.substring(1),
            sURLVariables = sPageURL.split(/[&||?]/),
            res;
        for (var i = 0; i < sURLVariables.length; i += 1) {
            var paramName = sURLVariables[i],
                sParameterName = (paramName || '').split('=');
            if (sParameterName[0] === param) {
                res = sParameterName[1];
            }
        }
        return res;
    }
    if (querystr.indexOf('=') == -1) {
        var a = querystr.split('/')
        scripcode = a[6];
        type = a[5];
        if (a.length > 7 && a[7] == "flag") {
            flag = a[8];
            nqtrid = a[7];
        }
    }
    else {
        scripcode = $scope.getUrlParameter('scripcode', querystr);
        flag = $scope.getUrlParameter('flag', querystr);
    }
    $rootScope.scripcode = scripcode;
    $scope.selperiod = flag;

    $scope.checknull = function (entnum) {
        if (entnum == null || entnum == undefined || entnum == "" || entnum == 0)
            return true;
        else
            return false;
    }

    $scope.getnsurl = function (flag, scripcode, nqtrid) {
        var qtrid = nqtrid.replace("&Flag=New", "")
        if (flag == "1")
            $scope.nsurl = "/stock-share-price/shp-latest/scripcode/" + script + "/qtrid/" + qtrid + "/";
        // $scope.nsurl = "/corporates/shpSecurities.aspx?scripcd=" + script + "&qtrid=" + nqtrid;
        else if (qtrid > 49) {
            $scope.nsurl = "/corporates/ShareholdingPattern.aspx?scripcd=" + script + "&flag_qtr=1&qtrid=" + qtrid + "&Flag=New";
        }
        else {

            $scope.nsurl = "/corporates/ShareholdingPattern.aspx?scripcd=" + script + "&flag_qtr=1&qtrid=" + qtrid;
        }
    }

    $scope.fn_Shrhld_Quarter = function () {
        $scope.loader.SHState = 'loading';
        $scope.loader.SHdelay = false;
        var url = mainapi.newapi_domain + serviceurl14.url_Sharehld_SHPQuarter;
        var urlF = $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode } }).then(function (response) {

            $scope.ShrhldQuarter = response.data;
            $scope.loader.SHState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHdelay = true;
                $scope.loader.SHState = 'loading';
            }
        });
    };
    $scope.trustAsHtmlshp = function (string) {
        return $sce.trustAsHtml(string);
    };


    $scope.checkdebtscrip = function () {
        var deb = "/stock-share-price/debt-other/scripcode/" + $scope.scripcode + "/";
        if ($scope.scripcode >= 700000 && $scope.scripcode <= 999999) {
            return true;
        }
        else {
            return false;
        }

    };
}]);


//Function for shareholding latest
getquote.constant('serviceurl15', {
    url_Sharehld_flag: 'shpSecFlag/w',
    url_Sharehld_Summary: 'shpSecSummery_New/w',
    url_Sharehld_Decelaration: 'shpDecleraction/w'
});

getquote.controller('latestshrhldController', ['serviceurl15', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function latestshrhldController(serviceurl15, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {

    $scope.loader = {
        SHSecState: 'loading',
        SHSecdelay: false,
    };

    var querystr = $location.absUrl().replace(/[\\#,+()$~%":*<>{};]/g, '_');
    var qtrid = "";
    var scripcode;
    var type;
    var totalItems = 0;
    $scope.getUrlParameter = function (param, dummyPath) {
        var sPageURL = dummyPath || window.location.search.substring(1),
            sURLVariables = sPageURL.split(/[&||?]/),
            res;
        for (var i = 0; i < sURLVariables.length; i += 1) {
            var paramName = sURLVariables[i],
                sParameterName = (paramName || '').split('=');
            if (sParameterName[0] === param) {
                res = sParameterName[1];
            }
        }
        return res;
    }
    if (querystr.indexOf('=') == -1) {
        var a = querystr.split('/')
        scripcode = a[6];
        type = a[5];
        if (a.length > 7 && a[7] == "qtrid") {
            qtrid = a[8];
        }
    }
    else {
        scripcode = $scope.getUrlParameter('scripcode', querystr);
        qtrid = $scope.getUrlParameter('qtrid', querystr);
    }
    $scope.qtrid = qtrid;
    $rootScope.scripcode = scripcode;

    $scope.fn_Shrhld_SecFlag = function () {
        $scope.loader.SHSecState = 'loading';
        $scope.loader.SHSecdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl15.url_Sharehld_flag;
        $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode, qtrid: $scope.qtrid } }).then(function (response) {
            $scope.ShrhldFlag = response.data;
            $scope.loader.SHSecState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHSecdelay = true;
                $scope.loader.SHSecState = 'loading';
            }
        });
    }

    $scope.fn_Shrhld_SecSummary = function () {
        $scope.loader.SHSecState = 'loading';
        $scope.loader.SHSecdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl15.url_Sharehld_Summary;
        var urlF = $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode, qtrid: $scope.qtrid } }).then(function (response) {

            $scope.ShrhldSummary = response.data;
            $scope.loader.SHSecState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHSecdelay = true;
                $scope.loader.SHSecState = 'loading';
                $scope.Norecordfound = "No Record Found";
            }
        });
    }
    $scope.fn_ShpDeclaration = function () {
        $scope.loader.SHSecState = 'loading';
        $scope.loader.SHSecdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl15.url_Sharehld_Decelaration;
        var urlF = $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode, qtrid: $scope.qtrid } }).then(function (response) {
            $scope.ShrhldDeclaration = response.data;
            $scope.loader.SHSecState = 'loaded';
            $scope.fn_shareholdingTitle($scope.ShrhldDeclaration[0].qtr_name);
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHSecdelay = true;
                $scope.loader.SHSecState = 'loading';

            }
        });
    }

    $scope.trustAsHtmllshp = function (string) {
        return $sce.trustAsHtml(string);
    };

    $scope.fn_shareholdingTitle = function (quter) {
        var strkeywords = "";
        var strDescp = "";
        var strRawUrl = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
        var strRawUrl1 = $location.absUrl().replace(/[\\#,+()$~%"*<>{};]/g, '_');
        var strArray = strRawUrl.split('/');
        if (strArray != null && strArray.length > 5) {
            strkeywords = "<meta name='keywords' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " shareholding pattern " + quter + ", " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " SHP " + quter + " , " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Owners, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Promoters, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Institution Shareholding, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Promoter Group, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Beneficial Owners, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " FII holding, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Institutional holding, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Domestic Institution holdings, BSE, BSEIndia '/>";
            strkeywords = strkeywords.replace("-", " ");
            strDescp = "<meta name='description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Shareholding pattern on quarterly basis, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Ownership' />";
            strDescp = strDescp.replace("-", " ");
            $('meta[name=description]').remove();
            $('meta[name=keywords]').remove();
            $(strkeywords).appendTo(document.head);
            $(strDescp).appendTo(document.head);

            var strtwittertitle = "<meta name='twitter:title' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " shareholding pattern " + quter + ", " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " SHP " + quter + " , " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Owners, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Promoters, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Institution Shareholding, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Promoter Group, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Beneficial Owners, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " FII holding, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Institutional holding, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Domestic Institution holdings, BSE, BSEIndia '/>";
            strtwittertitle = strtwittertitle.replace("-", " ");
            $('meta[name="twitter:title"]').remove();
            $(strtwittertitle).appendTo(document.head);

            var strtwitterdes = "<meta name='twitter:description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Shareholding pattern on quarterly basis, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Ownership' />";
            strtwitterdes = strtwitterdes.replace("-", " ");
            $('meta[name="twitter:description"]').remove();
            $(strtwitterdes).appendTo(document.head);

            $('meta[name="twitter:url"]').remove();
            $("head").append("<meta name='twitter:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:url"]').remove();
            $("head").append("<meta property='og:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:title"]').remove();
            $("head").append("<meta property='og:title' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " shareholding pattern " + quter + ", " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " SHP " + quter + " , " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Owners, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Promoters, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Institution Shareholding, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Promoter Group, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Beneficial Owners, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " FII holding, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Institutional holding, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Domestic Institution holdings, BSE, BSEIndia '/>");

            $('meta[property="og:description"]').remove();
            $("head").append("<meta property='og:description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Shareholding pattern on quarterly basis, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Ownership' />");
        }
        document.title = $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Shareholding Pattern, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " SHP, |BSE";
    }

}]);



//Function For shareholding meeting
getquote.constant('serviceurl16', {
    url_sharehlding: 'ShareHolderMeeting/w'
});
getquote.controller('eqshareholdingController', ['serviceurl16', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqshareholdingController(serviceurl16, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {


    $scope.loader = {
        SHState: 'loading',
        SHdelay: false,
    };

    $scope.fn_sharehlding = function () {
        $scope.loader.SHState = 'loading';
        $scope.loader.SHdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl16.url_sharehlding;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode } }).then(function successCallback(response) {
            $scope.SHData = response.data;
            $scope.loader.SHState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHdelay = true;
                $scope.loader.SHState = 'loading';
            }
        });
    }

    $rootScope.$on('$includeContentLoaded', function (event, url) {
        //console.log(event);
        //console.log(url);
        if (url == '/GetQuote/stk_shareholdingmeeting.html') {
            $('#collapse3').removeClass("panel-collapse collapse");
            $('#collapse3').addClass("panel-collapse collapse in");
            $('#l72').removeClass("panel panel-active");
            $('#l72').addClass("list-group-item");
            var cls = $('#collapse3').attr('class');
            if (cls == 'panel-collapse collapse in') {
                $('#l72').removeClass("list-group-item");
                $('#l72').addClass("panel panel-active");
                $('#l72').parent().addClass("divpanel-ative");
                $('#collapse3').css('display', 'block');
            }
        }
    });

    $scope.fn_shareTitle = function () {
        var strtwittertitle = "";
        var strtwitterdes = "";
        var strkeywords = "";
        var strDescp = "";
        var strRawUrl = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
        var strRawUrl1 = $location.absUrl().replace(/[\\#,+()$~%"*<>{};]/g, '_');
        var strArray = strRawUrl.split('/');
        if (strArray != null && strArray.length > 5) {

            strkeywords = "<meta name='keywords' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Shareholders Meeting," + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " AGM, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " EGM, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Annual General Meeting, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Extra-ordinary General Meeting, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Postal Ballot, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Court Convened Meetings, BSE, BSEIndia /'>";
            strkeywords = strkeywords.replace("-", " ");
            strDescp = "<meta name='description' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Shareholders Meetings, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " AGM, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " EGM. ' />";
            strDescp = strDescp.replace("-", " ");
            $('meta[name=description]').remove();
            $('meta[name=keywords]').remove();
            $(strkeywords).appendTo(document.head);
            $(strDescp).appendTo(document.head);

            strtwittertitle = "<meta name='twitter:title' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Shareholders Meeting," + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " AGM, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " EGM, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Annual General Meeting, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Extra-ordinary General Meeting, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Postal Ballot, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Court Convened Meetings, BSE, BSEIndia /'>";
            strtwittertitle = strtwittertitle.replace("-", " ");
            $('meta[name="twitter:title"]').remove();
            $(strtwittertitle).appendTo(document.head);

            strtwitterdes = "<meta name='twitter:description' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Shareholders Meetings, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " AGM, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " EGM. ' />";
            strtwitterdes = strtwitterdes.replace("-", " ");
            $('meta[name="twitter:description"]').remove();
            $(strtwitterdes).appendTo(document.head);

            $('meta[name="twitter:url"]').remove();
            $("head").append("<meta name='twitter:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:url"]').remove();
            $("head").append("<meta property='og:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:title"]').remove();
            $("head").append("<meta property='og:title' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Shareholders Meeting," + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " AGM, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " EGM, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Annual General Meeting, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Extra-ordinary General Meeting, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Postal Ballot, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Court Convened Meetings, BSE, BSEIndia /'>");

            $('meta[property="og:description"]').remove();
            $("head").append("<meta property='og:description' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Shareholders Meetings, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " AGM, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " EGM. ' />");
        }
        document.title = $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Shareholders Meetings, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " AGM ," + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " EGM | BSE";
    }
    $scope.fn_shareTitle();
}]);

//Function For investor complaints
getquote.constant('serviceurl17', {
    url_eqxbrlcomp: 'investorComplaint/w',
    url_eqxbrlcompinvits: 'investorComplaintInvits/w'
});
getquote.controller('eqinvestorcomplaintsController', ['serviceurl17', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqinvestorcomplaintsnewController(serviceurl17, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {


    var querystr = $location.absUrl().replace(/[\\#,+()$~%":*<>{};]/g, '_');
    var qtrid = "";
    var scripcode;
    var type;
    var totalItems = 0;
    $scope.getUrlParameter = function (param, dummyPath) {
        var sPageURL = dummyPath || window.location.search.substring(1),
            sURLVariables = sPageURL.split(/[&||?]/),
            res;
        for (var i = 0; i < sURLVariables.length; i += 1) {
            var paramName = sURLVariables[i],
                sParameterName = (paramName || '').split('=');
            if (sParameterName[0] === param) {
                res = sParameterName[1];
            }
        }
        return res;
    }
    if (querystr.indexOf('=') == -1) {
        var a = querystr.split('/')
        scripcode = a[6];
        type = a[5];
        if (a.length > 7 && a[7] == "qtrid") {
            qtrid = a[8];
        }
        if (a.length >= 10 && a[10] != "") {
            $scope.QuaterName = a[10];
        }
    }
    else {
        scripcode = $scope.getUrlParameter('scripcode', querystr);
        qtrid = $scope.getUrlParameter('qtrid', querystr);
    }
    $scope.qtrid = qtrid;
    $rootScope.scripcode = scripcode;

    $scope.loader = {
        SHState: 'loading',
        SHdelay: false,
    };

    $scope.fn_eqxbrlcomp = function () {
        $scope.loader.SHState = 'loading';
        $scope.loader.SHdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl17.url_eqxbrlcomp;
        $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode, qtrid: $scope.qtrid } }).then(function successCallback(response) {
            $scope.xbrlcomp = response.data;
            // console.log($scope.xbrlcompnew);
            $scope.loader.SHState = 'loaded';
            $scope.QuaterName = $scope.xbrlcomp.Table[0].Quarter;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHdelay = true;
                $scope.loader.SHState = 'loading';
            }
        });
    }
    $scope.fn_eqxbrlcompinvits = function () {
        $scope.loader.SHState = 'loading';
        $scope.loader.SHdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl17.url_eqxbrlcompinvits;
        $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode, qtrid: $scope.qtrid } }).then(function successCallback(response) {
            $scope.xbrlcompnew = response.data;
            //   console.log($scope.xbrlcompnew);
            $scope.loader.SHState = 'loaded';
            $scope.QuaterName = $scope.xbrlcompnew.Table[0].Quarter;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHdelay = true;
                $scope.loader.SHState = 'loading';
            }
        });
    }
    $scope.checknull = function (entnum) {
        if (entnum == null || entnum == undefined || entnum == "" || entnum == 0)
            return true;
        else
            return false;
    }

}]);


getquote.constant('serviceurl18', {
    url_sic: 'XbrlInvestorComplaint/w'
});
getquote.controller('eqsicController', ['serviceurl18', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqsicController(serviceurl18, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {


    $scope.loader = {
        SHState: 'loading',
        SHdelay: false,
    };

    var querystr = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
    var flag;
    var scripcode;
    var type;
    var qtrid;
    $scope.getUrlParameter = function (param, dummyPath) {
        var sPageURL = dummyPath || window.location.search.substring(1),
            sURLVariables = sPageURL.split(/[&||?]/),
            res;
        for (var i = 0; i < sURLVariables.length; i += 1) {
            var paramName = sURLVariables[i],
                sParameterName = (paramName || '').split('=');
            if (sParameterName[0] === param) {
                res = sParameterName[1];
            }
        }
        return res;
    }
    if (querystr.indexOf('=') == -1) {
        var a = querystr.split('/')
        scripcode = a[6];
        type = a[5];
        if (a.length > 7 && a[7] == "flag") {
            flag = a[8];
            nqtrid = a[7];
        }
    }
    else {
        scripcode = $scope.getUrlParameter('scripcode', querystr);
        flag = $scope.getUrlParameter('flag', querystr);
    }
    $rootScope.scripcode = scripcode;
    $scope.selperiod = flag;

    $scope.checknull = function (entnum) {
        if (entnum == null || entnum == undefined || entnum == "" || entnum == 0)
            return true;
        else
            return false;
    }



    $scope.fn_sic_Quarter = function () {
        $scope.loader.SHState = 'loading';
        $scope.loader.SHdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl18.url_sic;
        var urlF = $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode } }).then(function (response) {
            $scope.sicQuarter = response.data;
            $scope.loader.SHState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHdelay = true;
                $scope.loader.SHState = 'loading';
            }
        });
    };
    $scope.checkdebtscrip = function () {
        var deb = "/stock-share-price/debt-other/scripcode/" + $scope.scripcode + "/";
        if ($scope.scripcode >= 700000 && $scope.scripcode <= 999999) {
            return true;
        }
        else {
            return false;
        }

    };

}]);
//Function For related-party-transactions
getquote.constant('serviceurl19', {
    url_eqpartytransactions: 'XbrlRPTDetails/w',
    url_eqpartytransactionsnew: 'XbrlRPTDetailsNewFormat/w'
});

getquote.controller('eqpartytransactionsController', ['serviceurl19', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqpartytransactionsController(serviceurl19, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {


    $scope.loader = {
        SHState: 'loading',
        SHdelay: false,
    };

    var querystr = $location.absUrl().replace(/[\\#,+()$~%":*<>{};]/g, '_');
    var qtrid = "";
    var scripcode;
    var type;
    var totalItems = 0;
    $scope.getUrlParameter = function (param, dummyPath) {
        var sPageURL = dummyPath || window.location.search.substring(1),
            sURLVariables = sPageURL.split(/[&||?]/),
            res;
        for (var i = 0; i < sURLVariables.length; i += 1) {
            var paramName = sURLVariables[i],
                sParameterName = (paramName || '').split('=');
            if (sParameterName[0] === param) {
                res = sParameterName[1];
            }
        }
        return res;
    }
    if (querystr.indexOf('=') == -1) {
        var a = querystr.split('/')
        scripcode = a[6];
        type = a[5];
        if (a.length > 7 && a[7] == "qtrid") {
            qtrid = a[8];
        }
        if (a.length >= 10 && a[10] != "") {
            $scope.QuaterName = a[10];
        }
    }
    else {
        scripcode = $scope.getUrlParameter('scripcode', querystr);
        qtrid = $scope.getUrlParameter('qtrid', querystr);
    }
    $scope.qtrid = qtrid;
    $rootScope.scripcode = scripcode;

    $scope.fn_eqpartytransactions = function () {
        $scope.loader.SHState = 'loading';
        $scope.loader.SHdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl19.url_eqpartytransactions;
        $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode, qtrid: $scope.qtrid } }).then(function successCallback(response) {
            $scope.partytransactions = response.data;
            $scope.loader.SHState = 'loaded';
            if ($scope.partytransactions != '') {
                var strv = $scope.partytransactions.split('##');
                $scope.QuaterName = strv[1];
                $scope.partytransactionsnew = strv[0];
            }
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHdelay = true;
                $scope.loader.SHState = 'loading';
            }
        });
    }

    $scope.fn_eqpartytransactionsNew = function () {
        $scope.loader.SHState = 'loading';
        $scope.loader.SHdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl19.url_eqpartytransactionsnew;
        $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode, qtrid: $scope.qtrid } }).then(function successCallback(response) {
            $scope.partreltbl = response.data;
            $scope.loader.SHState = 'loaded';
            if ($scope.partreltbl != '') {
                var strv = $scope.partreltbl.Table[0].QUARTER;
                $scope.QuaterName = strv;
            }
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHdelay = true;
                $scope.loader.SHState = 'loading';
            }
        });
    }

    $scope.checknull = function (entnum) {
        if (entnum == null || entnum == undefined || entnum == "" || entnum == 0)
            return true;
        else
            return false;
    }
    $scope.trustAsHtmlrpt = function (string) {
        return $sce.trustAsHtml(string);
    };
}]);

getquote.constant('serviceurl20', {
    url_prt: 'XbrlRelatedPartyTrans/w'
});
getquote.controller('eqprtController', ['serviceurl20', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqprtController(serviceurl20, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {




    $scope.loader = {
        PRTState: 'loading',
        PRTdelay: false,
    };

    var querystr = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
    var flag;
    var scripcode;
    var type;
    var qtrid;
    $scope.getUrlParameter = function (param, dummyPath) {
        var sPageURL = dummyPath || window.location.search.substring(1),
            sURLVariables = sPageURL.split(/[&||?]/),
            res;
        for (var i = 0; i < sURLVariables.length; i += 1) {
            var paramName = sURLVariables[i],
                sParameterName = (paramName || '').split('=');
            if (sParameterName[0] === param) {
                res = sParameterName[1];
            }
        }
        return res;
    }
    if (querystr.indexOf('=') == -1) {
        var a = querystr.split('/')
        scripcode = a[6];
        type = a[5];
        if (a.length > 7 && a[7] == "flag") {
            flag = a[8];
            nqtrid = a[7];
        }
    }
    else {
        scripcode = $scope.getUrlParameter('scripcode', querystr);
        flag = $scope.getUrlParameter('flag', querystr);
    }
    $rootScope.scripcode = scripcode;
    $scope.selperiod = flag;

    $scope.fn_prt_Quarter = function () {
        $scope.loader.PRTState = 'loading';
        $scope.loader.PRTdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl20.url_prt;
        var urlF = $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode } }).then(function (response) {
            $scope.prtQuarter = response.data;
            $scope.loader.PRTState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.PRTdelay = true;
                $scope.loader.PRTState = 'loading';
            }
        });
    };

    //$scope.fn_navigate = function (nsurl, navurl) {
    //    var deb = "/stock-share-price/debt-other/scripcode/" + $scope.scripcode + "/";
    //    if ($scope.scripcode >= 700000 && $scope.scripcode <= 999999) {
    //        $scope.navigatesurl = navurl.replace(nsurl, deb);
    //    }
    //    else {
    //       $scope.navigateurl = navurl;
    //    }
    //};

    $scope.checkdebtscrip = function () {
        var deb = "/stock-share-price/debt-other/scripcode/" + $scope.scripcode + "/";
        if ($scope.scripcode >= 700000 && $scope.scripcode <= 999999) {
            return true;
        }
        else {
            return false;
        }

    };

    $scope.checknull = function (entnum) {
        if (entnum == null || entnum == undefined || entnum == "" || entnum == 0)
            return true;
        else
            return false;
    }
}]);

//Function For brsr

getquote.constant('serviceurl21', {
    url_brsr: 'XbrlBrsrDetails/w'
});
getquote.controller('eqbrsrController', ['serviceurl21', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqbrsrController(serviceurl21, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {


    $scope.loader = {
        SHState: 'loading',
        SHdelay: false,
    };

    var querystr = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
    var flag;
    var scripcode;
    var type;
    var qtrid;
    $scope.getUrlParameter = function (param, dummyPath) {
        var sPageURL = dummyPath || window.location.search.substring(1),
            sURLVariables = sPageURL.split(/[&||?]/),
            res;
        for (var i = 0; i < sURLVariables.length; i += 1) {
            var paramName = sURLVariables[i],
                sParameterName = (paramName || '').split('=');
            if (sParameterName[0] === param) {
                res = sParameterName[1];
            }
        }
        return res;
    }
    if (querystr.indexOf('=') == -1) {
        var a = querystr.split('/')
        scripcode = a[6];
        type = a[5];
        if (a.length > 7 && a[7] == "brsr") {
        }
    }
    else {
        scripcode = $scope.getUrlParameter('scripcode', querystr);
        //flag = $scope.getUrlParameter('flag', querystr);
    }
    $rootScope.scripcode = scripcode;
    $scope.selperiod = 0;

    $scope.checknull = function (entnum) {
        if (entnum == null || entnum == undefined || entnum == "" || entnum == 0)
            return true;
        else
            return false;
    }



    $scope.fn_brsr_Quarter = function () {
        $scope.loader.SHState = 'loading';
        $scope.loader.SHdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl21.url_brsr;
        var urlF = $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode } }).then(function (response) {
            $scope.brsrQuarter = response.data;
            $scope.loader.SHState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHdelay = true;
                $scope.loader.SHState = 'loading';
            }
        });
    };


}]);
//Function For ascr
getquote.constant('serviceurl31', {
    url_ascr: 'XbrlAscrDetails/w',
    url_ascrannx: 'Displayascrannxnew/w',

});
getquote.controller('eqascrController', ['serviceurl31', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqascrController(serviceurl31, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {


    $scope.loader = {
        ASState: 'loading',
        ASdelay: false,
    };

    var querystr = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
    var flag;
    var scripcode;
    var type;
    var qtrid;
    $scope.showascrDetails = false;
    $scope.ascrDetails = undefined;

    $scope.fn_ascrDetails = function (scode, authdate) {
        $scope.scode = scode;
        $scope.authdate = authdate;
        var url = mainapi.api_domainLIVE + serviceurl31.url_ascrannx;

        $http({ url: url, method: "GET", params: { scripcode: scode, authdate: authdate } }).then(function successCallback(response) {
            $scope.ascrDetails = response.data;

            $scope.showascrDetails = true;
            $('html, body').animate({
                scrollTop: $("#ascrhtmdata").offset().top
            }, 1000);
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
        });
    }

    $scope.trustAsHtmllascr = function (string) {
        return $sce.trustAsHtml(string);
    };


    $scope.getUrlParameter = function (param, dummyPath) {
        var sPageURL = dummyPath || window.location.search.substring(1),
            sURLVariables = sPageURL.split(/[&||?]/),
            res;
        for (var i = 0; i < sURLVariables.length; i += 1) {
            var paramName = sURLVariables[i],
                sParameterName = (paramName || '').split('=');
            if (sParameterName[0] === param) {
                res = sParameterName[1];
            }
        }
        return res;
    }
    if (querystr.indexOf('=') == -1) {
        var a = querystr.split('/')
        scripcode = a[6];
        type = a[5];
        if (a.length > 7 && a[7] == "ascr") {
        }
    }
    else {
        scripcode = $scope.getUrlParameter('scripcode', querystr);
        //flag = $scope.getUrlParameter('flag', querystr);
    }
    $rootScope.scripcode = scripcode;
    $scope.selperiod = 0;

    $scope.checknull = function (entnum) {
        if (entnum == null || entnum == undefined || entnum == "" || entnum == 0)
            return true;
        else
            return false;
    }

    $scope.ascrQuarter = undefined;

    $scope.fn_ascr_Quarter = function () {
        $scope.loader.ASState = 'loading';
        $scope.loader.ASdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl31.url_ascr;


        var urlF = $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode } }).then(function (response) {
            $scope.ascrQuarter = response.data;

            $scope.loader.ASState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.ASdelay = true;
                $scope.loader.ASState = 'loading';
            }
        });
    };


}]);
//Function For sast31

getquote.constant('serviceurl22', {
    url_sast31: 'regulation31data/w'
});
getquote.controller('eqsast31Controller', ['serviceurl22', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqsast31Controller(serviceurl22, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {

    $scope.loader = {
        SHState: 'loading',
        SHdelay: false,
    };

    var querystr = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
    var flag;
    var scripcode;
    var type;
    var qtrid;
    $scope.getUrlParameter = function (param, dummyPath) {
        var sPageURL = dummyPath || window.location.search.substring(1),
            sURLVariables = sPageURL.split(/[&||?]/),
            res;
        for (var i = 0; i < sURLVariables.length; i += 1) {
            var paramName = sURLVariables[i],
                sParameterName = (paramName || '').split('=');
            if (sParameterName[0] === param) {
                res = sParameterName[1];
            }
        }
        return res;
    }
    if (querystr.indexOf('=') == -1) {
        var a = querystr.split('/')
        scripcode = a[6];
        type = a[5];
        if (a.length > 7 && a[7] == "disclosures-sast-31") {
        }
    }
    else {
        scripcode = $scope.getUrlParameter('scripcode', querystr);
        //flag = $scope.getUrlParameter('flag', querystr);
    }
    $rootScope.scripcode = scripcode;
    $scope.selperiod = 0;

    $scope.checknull = function (entnum) {
        if (entnum == null || entnum == undefined || entnum == "" || entnum == 0)
            return true;
        else
            return false;
    }

    $scope.fn_sast_Quarter = function () {
        $scope.loader.SHState = 'loading';
        $scope.loader.SHdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl22.url_sast31;
        var urlF = $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode } }).then(function (response) {
            $scope.sastQuarter = response.data;
            $scope.loader.SHState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHdelay = true;
                $scope.loader.SHState = 'loading';
            }
        });
    };


}]);
//Start shareholding unit

getquote.constant('serviceurl23', {
    url_Shareddl_Unit: 'ShaDropdowndata/w',
    url_SharehldgUnit: 'unitholdingdetails/w',
    url_SHPUnitArcive: 'unitholdingarchive/w'
});
getquote.controller('shrhldUnitController', ['serviceurl23', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function shrhldUnitController(serviceurl23, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {



    $scope.loader = {
        SHUnitState: 'loading',
        SHUnitdelay: false,
    };

    var querystr = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
    var flag;
    var scripcode;
    var type;
    var qtrid;
    $scope.getUrlParameter = function (param, dummyPath) {
        var sPageURL = dummyPath || window.location.search.substring(1),
            sURLVariables = sPageURL.split(/[&||?]/),
            res;
        for (var i = 0; i < sURLVariables.length; i += 1) {
            var paramName = sURLVariables[i],
                sParameterName = (paramName || '').split('=');
            if (sParameterName[0] === param) {
                res = sParameterName[1];
            }
        }
        return res;
    }

    if (querystr.indexOf('=') == -1) {
        var a = querystr.split('/')
        scripcode = a[6];
        type = a[5];
        if (a.length > 7 && a[7] == "flag") {
            flag = a[8];
        }
        else if (a.length > 7 && a[7] == "qtrid") {
            qtrid = a[8];
            if (a.length >= 10 && a[10] != "") {
                $scope.QuaterName = a[10];
            }
        }
        else if (a.length > 7 && a[7] == "shpunit") {
        }

    }
    else {
        scripcode = $scope.getUrlParameter('scripcode', querystr);
        qtrid = $scope.getUrlParameter('qtrid', querystr);
        flag = $scope.getUrlParameter('flag', querystr);
    }
    $scope.qtrid = qtrid;
    $rootScope.scripcode = scripcode;
    $scope.selperiod = flag;
    $scope.flag = flag;
    if ($scope.selperiod == null || $scope.selperiod == undefined || $scope.selperiod == "")
        $scope.selperiod = "1";
    $scope.selindustry = "0";

    //For pagination
    $scope.viewby = 25;
    $scope.totalItems = 0;
    $scope.currentPage = 1;
    $scope.itemsPerPage = $scope.viewby;
    $scope.maxSize = 5; //Number of pager buttons to show

    $scope.fn_Shrhld_Unit = function () {

        $scope.loader.SHUnitState = 'loading';
        $scope.loader.SHUnitdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl23.url_SharehldgUnit;
        $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode, qtrid: $scope.qtrid } }).then(function (response) {

            $scope.ShrhldUnit = response.data;

            $scope.loader.SHUnitState = 'loaded';
            //  $scope.currentPage = 1;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHdelay = true;
                $scope.loader.SHState = 'loading';
            }
        });
    }
    $scope.selectChng = function () {
        //$scope.selperiod = $scope.selperiod;
        //if ($scope.selperiod == "1" || $scope.selperiod == "2" || $scope.selperiod == "3" || $scope.selperiod == "4" || $scope.selperiod == "5" || $scope.selperiod == "6" || $scope.selperiod == "7")
        { $scope.fn_Shrhld_Unit(); }
    }

    $scope.checknull = function (entnum) {
        if (entnum == null || entnum == undefined || entnum == "" || entnum == 0)
            return true;
        else
            return false;
    }
    $scope.getnsurl = function (flag, script, nqtrid) {

        if (flag == "1")
            $scope.nsurl = "/corporates/shpSecurities.aspx?scripcd=" + script + "&qtrid=" + nqtrid;
        else
            $scope.nsurl = "/corporates/ShareholdingPattern.aspx?scripcd=" + script + "&flag_qtr=1&qtrid=" + nqtrid;
    }



    $scope.fn_Arc_Quarter = function () {
        $scope.loader.SHUnitState = 'loading';
        $scope.loader.SHUnitdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl23.url_SHPUnitArcive;
        var urlF = $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode } }).then(function (response) {
            $scope.arcQuarter = response.data;
            $scope.loader.SHUnitState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHUnitdelay = true;
                $scope.loader.SHUnitState = 'loading';
            }
        });
    };

}]);

//end share holding controller


getquote.constant('serviceurl24', {
    url_votingresult: 'VotingResults/w',
    url_meetingdetails: 'MeetingDetails/w'
});
getquote.controller('eqvotingresultController', ['serviceurl24', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqvotingresultController(serviceurl24, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {



    $scope.loader = {

        VRState: 'loading',
        VRdelay: false,
    };

    var querystr = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
    var scripcode;
    $scope.MeetingType = "0";
    $scope.FromDate = "";
    $scope.ToDate = "";
    //$scope.filteredRes = undefined;
    $scope.VResults = undefined;
    $scope.showMtDetails = false;
    $scope.MtDetails = undefined;

    $scope.fn_MeetingDetails = function (masterid, fld_srno, resoln, resolntype, agenda) {
        $scope.Masterid = masterid;
        $scope.Srno = fld_srno;
        var url = mainapi.api_domainLIVE + serviceurl24.url_meetingdetails;
        $http({ url: url, method: "GET", params: { mid: masterid, srno: fld_srno } }).then(function successCallback(response) {
            $scope.MtDetails = response.data;
            if (resoln != "")
                $scope.MtDetails.Resolution = resoln;
            if (resolntype != "")
                $scope.MtDetails.Resolntype = resolntype;
            if (agenda.toString() != "")
                $scope.MtDetails.Agenda = agenda;
            $scope.showMtDetails = true;
            $('html, body').animate({
                scrollTop: $("#meetngdata").offset().top
            }, 1000);
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
        });
    }

    $scope.getUrlParameter = function (param, dummyPath) {
        var sPageURL = dummyPath || window.location.search.substring(1),
            sURLVariables = sPageURL.split(/[&||?]/),
            res;
        for (var i = 0; i < sURLVariables.length; i += 1) {
            var paramName = sURLVariables[i],
                sParameterName = (paramName || '').split('=');
            if (sParameterName[0] === param) {
                res = sParameterName[1];
            }
        }
        return res;
    }
    if (querystr.indexOf('=') == -1) {
        var a = querystr.split('/')
        if (a.length > 5) {
            scripcode = a[6];
            type = a[5];
            if (a.length > 8 && a[8] != "") {
                $scope.Masterid = parseInt(a[7]);
                $scope.Srno = parseInt(a[8]);
                $scope.Mtype = a[9];
                $scope.fn_MeetingDetails($scope.Masterid, $scope.Srno, "", "", "");
            }
        }
    }
    else {
        scripcode = $scope.getUrlParameter('scripcode', querystr);
    }

    $scope.scripcode = scripcode;

    if ($scope.scripcode == null || $scope.scripcode == undefined) {
        $scope.scripcode = 000;//500325;//501479;//503772;
    }

    $scope.loader = {
        loading: false,
        loaded: false,
    }

    $scope.fn_votingresult = function () {
        $scope.loader.VRState = 'loading';
        $scope.loader.VRdelay = false;
        $scope.filteredRes = undefined;
        var url = mainapi.api_domainLIVE + serviceurl24.url_votingresult;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, type: $scope.MeetingType, fromdt: $scope.FromDate, todt: $scope.ToDate } }).then(function successCallback(response) {
            $scope.VResults = response.data;
            $scope.loader.VRState = 'loaded';
            if ($scope.VResults != null && $scope.VResults.Table.length > 0 && $scope.Masterid != undefined) {
                $scope.meeting = $scope.seltdmting($scope.VResults.Table);
                if ($scope.meeting != null) {
                    $scope.MtDetails.Resolution = $scope.meeting.Fld_AgendaDetails;
                    $scope.MtDetails.Resolntype = $scope.meeting.Fld_ResolTypeID.split('#')[0].trim();
                    $scope.MtDetails.Agenda = $scope.meeting.Fld_AgendaInterest;
                }
            }

        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.VRdelay = true;
                $scope.loader.VRState = 'loading';
            }
        });
    }

    $scope.seltdmting = function (meeting) {
        for (var i = 0; i < meeting.length; i++) {
            if (meeting[i].Fld_MasterID == $scope.Masterid && meeting[i].fld_srno == $scope.Srno)
                return meeting[i];
        }
    }

    $scope.fn_submit_v = function () {
        if ($scope.FromDate != "" && $scope.ToDate == "") {
            alert("Please Enter To Date.");
        }
        else if ($scope.FromDate == "" && $scope.ToDate != "") {
            alert("Please Enter From Date.");
        }
        else if ($scope.FromDate != "" && $scope.ToDate != "") {
            var fromdt = new Date($scope.FromDate.split('/')[2], $scope.FromDate.split('/')[1] - 1, $scope.FromDate.split('/')[0]);
            var todt = new Date($scope.ToDate.split('/')[2], $scope.ToDate.split('/')[1] - 1, $scope.ToDate.split('/')[0]);
            if (fromdt > todt)
                alert("From date should not be lesser than To date.");
            else
                $scope.fn_votingresult();
        }
        else {

            $scope.fn_votingresult();
        }
    }

    $scope.fn_reset = function () {
        $scope.MeetingType = "0";
        $scope.FromDate = "";
        $scope.ToDate = "";

        $scope.fn_votingresult();
    }

    $scope.checknull = function (entnum) {
        if (entnum == null || entnum == undefined || entnum == "" || entnum == 0)
            return true;
        else
            return false;
    }

    $scope.trustAsHtmllvot = function (string) {
        return $sce.trustAsHtml(string);
    };


    $rootScope.$on('$includeContentLoaded', function (event, url) {

        if (url == '/GetQuote/stk_votingresults.html') {
            $('#collapse3').removeClass("panel-collapse collapse");
            $('#collapse3').addClass("panel-collapse collapse in");
            $('#l73').removeClass("panel panel-active");
            $('#l73').addClass("list-group-item");
            var cls = $('#collapse3').attr('class');
            if (cls == 'panel-collapse collapse in') {
                $('#l73').removeClass("list-group-item");
                $('#l73').addClass("panel panel-active");
                $('#l73').parent().addClass("divpanel-ative");
                $('#collapse3').css('display', 'block');

            }
        }
    });

    $scope.fn_votingTitle = function () {
        var strtwittertitle = "";
        var strtwitterdes = "";
        var strkeywords = "";
        var strDescp = "";
        var strRawUrl = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
        var strRawUrl1 = $location.absUrl().replace(/[\\#,+()$~%"*<>{};]/g, '_');
        var strArray = strRawUrl.split('/');
        if (strArray != null && strArray.length > 5) {

            strkeywords = "<meta name='keywords' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Voting Results for AGM, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Voting Results for EGM, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Voting Results for Postal Ballot, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Voting Results for Court Convened Meeting, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Voting Results for Annual General Meeting, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Voting Results for Extra-ordinary General Meeting," + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Voting Results meeting purpose, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Voting Results meeting date, BSE, BSEIndia /'>";
            strkeywords = strkeywords.replace("-", " ");
            strDescp = "<meta name='description' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Voting Results  /'>";
            strDescp = strDescp.replace("-", " ");
            $('meta[name=description]').remove();
            $('meta[name=keywords]').remove();
            $(strkeywords).appendTo(document.head);
            $(strDescp).appendTo(document.head);

            strtwittertitle = "<meta name='twitter:title' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Voting Results for AGM, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Voting Results for EGM, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Voting Results for Postal Ballot, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Voting Results for Court Convened Meeting, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Voting Results for Annual General Meeting, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Voting Results for Extra-ordinary General Meeting," + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Voting Results meeting purpose, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Voting Results meeting date, BSE, BSEIndia /'>";
            strtwittertitle = strtwittertitle.replace("-", " ");
            $('meta[name="twitter:title"]').remove();
            $(strtwittertitle).appendTo(document.head);

            strtwitterdes = "<meta name='twitter:description' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Voting Results  /'>";
            strtwitterdes = strtwitterdes.replace("-", " ");
            $('meta[name="twitter:description"]').remove();
            $(strtwitterdes).appendTo(document.head);

            $('meta[name="twitter:url"]').remove();
            $("head").append("<meta name='twitter:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:url"]').remove();
            $("head").append("<meta property='og:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:title"]').remove();
            $("head").append("<meta property='og:title' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Voting Results for AGM, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Voting Results for EGM, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Voting Results for Postal Ballot, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Voting Results for Court Convened Meeting, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Voting Results for Annual General Meeting, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Voting Results for Extra-ordinary General Meeting," + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Voting Results meeting purpose, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Voting Results meeting date, BSE, BSEIndia /'>");

            $('meta[property="og:description"]').remove();
            $("head").append("<meta property='og:description' content='" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Voting Results  /'>");
        }
        document.title = $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Voting Results, |BSE ";
    }
    $scope.fn_votingTitle();
}]);

//Function For sast
getquote.constant('serviceurl25', {
    url_SAST: "SAST/w",
    url_DwnldExcelsas: "DwnldExcel_SAST/w"
});
getquote.controller('eqsastController', ['serviceurl25', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqsastController(serviceurl25, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {



    $scope.loader = {
        STOCKState: 'loading',
        STOCKdelay: false,
    };
    //var querystr = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
    //var scripcode;
    //$scope.getUrlParameter = function (param, dummyPath) {
    //    var sPageURL = dummyPath || window.location.search.substring(1),
    //               sURLVariables = sPageURL.split(/[&||?]/),
    //               res;
    //    for (var i = 0; i < sURLVariables.length; i += 1) {
    //        var paramName = sURLVariables[i],
    //             sParameterName = (paramName || '').split('=');
    //        if (sParameterName[0] === param) {
    //            res = sParameterName[1];
    //        }
    //    }
    //    return res;
    //}
    //if (querystr.indexOf('=') == -1) {
    //    var a = querystr.split('/')
    //    scripcode = a[6];
    //    type = a[5];
    //}
    //else {
    //    scripcode = $scope.getUrlParameter('scripcode', querystr);
    //}
    //$scope.scripcode = scripcode;
    //if ($scope.scripcode == null || $scope.scripcode == undefined) {
    //    $scope.scripcode = 000;//500325;//501479;//503772;
    //}



    $scope.FromDate = '';
    $scope.ToDate = '';
    $scope.totalItems = 0;
    $scope.currentPage = 1;
    $scope.itemsPerPage = 25;
    $scope.maxSize = 5; //Number of pager buttons to show

    $scope.fn_SAST = function () {
        $scope.loader.STOCKState = 'loading';
        $scope.loader.STOCKdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl25.url_SAST;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, fromdt: $scope.FromDate, todt: $scope.ToDate } }).then(function successCallback(response) {
            $scope.SAST = response.data;
            $scope.loader.STOCKState = 'loaded';
            $scope.totalItems = $scope.SAST.Table.length;
            $scope.currentPage = 1;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.STOCKdelay = true;
                $scope.loader.STOCKState = 'loading';
            }
        });
    }

    $scope.fn_submit = function () {
        if ($scope.FromDate != "" && $scope.ToDate != "") {
            var fmdt = new Date($scope.FromDate.split('/')[2], $scope.FromDate.split('/')[1] - 1, $scope.FromDate.split('/')[0]);
            var todt = new Date($scope.ToDate.split('/')[2], $scope.ToDate.split('/')[1] - 1, $scope.ToDate.split('/')[0]);
            if (fmdt > todt) {
                alert('From date should be less than To date'); return;
            }
            else {
                $scope.fn_SAST();
            }
        }
        else if ($scope.FromDate != "" && $scope.ToDate == "") {
            alert('Please enter From Date');
        }
        else if ($scope.FromDate == "" && $scope.ToDate != "") {
            alert('Please enter To Date');
        }
    }

    $scope.fn_downloadexcel = function () {
        var url = mainapi.api_domainLIVE + serviceurl25.url_DwnldExcelsas + "?scripcode=" + $scope.scripcode + "&fromdt=" + $scope.FromDate + "&todt=" + $scope.ToDate + "&flag=SAST";
        return url;
        //$http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, fromdt: $scope.FromDate, todt: $scope.ToDate, flag: 'InsiderTrade15' } }).then(function successCallback(response) {

        //}, function errorCallback(response) {
        //    $scope.status = response.status + "_" + response.statusText;
        //});
    }

    $rootScope.$on('$includeContentLoaded', function (event, url) {
        //console.log(event);
        //console.log(url);
        if (url == '/GetQuote/stk_sast.html') {
            $('#collapse4').removeClass("panel-collapse collapse");
            $('#collapse4').addClass("panel-collapse collapse in");
            $('#l123').removeClass("panel panel-active");
            $('#l123').addClass("list-group-item");
            var cls = $('#collapse4').attr('class');
            if (cls == 'panel-collapse collapse in') {
                $('#l123').removeClass("list-group-item");
                $('#l123').addClass("panel panel-active");
                $('#l123').parent().addClass("divpanel-ative");
                $('#collapse4').css('display', 'block');
            }
        }
    });

    $scope.fn_SASTTitle = function () {
        var strtwittertitle = "";
        var strtwitterdes = "";
        var strkeywords = "";
        var strDescp = "";
        var strRawUrl = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
        var strRawUrl1 = $location.absUrl().replace(/[\\#,+()$~%"*<>{};]/g, '_');
        var strArray = strRawUrl.split('/');
        if (strArray != null && strArray.length > 5) {
            strkeywords = "<meta name='keywords' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Substantial Acquisition of Shares and Takeovers " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " SAST, BSE, BSEIndia'/>";
            strkeywords = strkeywords.replace("-", " ");
            strDescp = "<meta name='description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Substantial Acquisition of Shares and Takeovers " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " SAST '/> ";
            strDescp = strDescp.replace("-", " ");
            $('meta[name=description]').remove();
            $('meta[name=keywords]').remove();
            $(strkeywords).appendTo(document.head);
            $(strDescp).appendTo(document.head);

            strtwittertitle = "<meta name='twitter:title' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Substantial Acquisition of Shares and Takeovers " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " SAST, BSE, BSEIndia'/>";
            strtwittertitle = strtwittertitle.replace("-", " ");
            $('meta[name="twitter:title"]').remove();
            $(strtwittertitle).appendTo(document.head);

            strtwitterdes = "<meta name='twitter:description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Substantial Acquisition of Shares and Takeovers " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " SAST '/> ";
            strtwitterdes = strtwitterdes.replace("-", " ");
            $('meta[name="twitter:description"]').remove();
            $(strtwitterdes).appendTo(document.head);

            $('meta[name="twitter:url"]').remove();
            $("head").append("<meta name='twitter:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:url"]').remove();
            $("head").append("<meta property='og:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:title"]').remove();
            $("head").append("<meta property='og:title' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Substantial Acquisition of Shares and Takeovers " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " SAST, BSE, BSEIndia'/>");

            $('meta[property="og:description"]').remove();
            $("head").append("<meta property='og:description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Substantial Acquisition of Shares and Takeovers " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " SAST '/> ");
        }
        document.title = $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Substantial Acquisition of Shares and Takeovers " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " SAST |BSE";
    }
    $scope.fn_SASTTitle();
}]);

//Function for research reports
getquote.constant('serviceurl26', {
    url_ResearchRpt: 'ResearchReport/w'
});
getquote.controller('eqresearchController', ['serviceurl26', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqresearchController(serviceurl26, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {



    $scope.loader = {
        loading: false,
        loaded: false,
    }
    $scope.FromDate = '';
    $scope.ToDate = '';

    $scope.fn_ResearchRpt = function () {
        var url = mainapi.api_domainLIVE + serviceurl26.url_ResearchRpt;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, todate: $scope.ToDate, fmdate: $scope.FromDate } }).then(function successCallback(response) {
            $scope.ResearchRpt = response.data;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
        });
    }

    $scope.fn_submit = function () {
        if ($scope.FromDate != "" && $scope.ToDate != "") {
            var fmdt = new Date($scope.FromDate.split('/')[2], $scope.FromDate.split('/')[1] - 1, $scope.FromDate.split('/')[0]);
            var todt = new Date($scope.ToDate.split('/')[2], $scope.ToDate.split('/')[1] - 1, $scope.ToDate.split('/')[0]);
            if (fmdt > todt) {
                alert('From date should be less than To date'); return;
            }
            else {
                $scope.fn_ResearchRpt();
            }
        }
        else if ($scope.FromDate != "" && $scope.ToDate == "") {
            alert('Please enter From Date');
        }
        else if ($scope.FromDate == "" && $scope.ToDate != "") {
            alert('Please enter To Date');
        }
    }

    $scope.checknull = function (entnum) {
        if (entnum == null || entnum == undefined || entnum == "" || entnum == 0)
            return true;
        else
            return false;
    }

}]);


//Function For corpinfo
getquote.constant('serviceurl27', {
    url_CorpInfo: 'CorpInfoNew/w',
    urlCorpInformation: 'CorpBoard/w',
    url_StatutoryAuditor: 'StatutoryAuditor/w'
});

//Corp Info Controller
getquote.controller('eqcorpinfoController', ['serviceurl27', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqcorpinfoController(serviceurl27, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {



    $scope.loader = {

        CIState: 'loading',
        CIdelay: false,

    };
    $scope.fn_CorpInfo = function () {
        $scope.loader.CIState = 'loading';
        $scope.loader.CIdelay = false;
        var url = mainapi.newapi_domain + serviceurl27.url_CorpInfo;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode } }).then(function successCallback(response) {
            $scope.CorpInfo = response.data;
            $scope.loader.CIState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.CIdelay = true;
                $scope.loader.CIState = 'loading';
            }
        });
    }

    $scope.fn_StatutoryAuditor = function (flg) {
        $scope.loader.CIState = 'loading';
        $scope.loader.CIdelay = false;
        var url = mainapi.newapi_domain + serviceurl27.url_StatutoryAuditor;
        $http({ url: url, method: "GET", params: { scode: $scope.scripcode, flag: flg } }).then(function successCallback(response) {
            $scope.StatutoryAuditor = response.data;
            $scope.loader.CIState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.CIdelay = true;
                $scope.loader.CIState = 'loading';
            }
        });
    }

    $scope.fn_CorpInfo_Url = function () {

        var url = mainapi.api_domainLIVE + serviceurl27.urlCorpInformation;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode } }).then(function successCallback(response) {

            $scope.CorpInfoUrl = response.data;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {

            }
        });
    }

    $rootScope.$on('$includeContentLoaded', function (event, url) {
        $('#l13').removeClass("panel panel-default");
        $('#l13').addClass("panel panel-active");
    });

    $scope.fn_corpInfoTitle = function () {
        var strtwittertitle = "";
        var strtwitterdes = "";
        var strkeywords = "";
        var strDescp = "";
        var strRawUrl = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
        var strRawUrl1 = $location.absUrl().replace(/[\\#,+()$~%"*<>{};]/g, '_');
        var strArray = strRawUrl.split('/');
        if (strArray != null && strArray.length > 5) {
            strkeywords = "<meta name='keywords' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Board of Directors & Management, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Board of Directors & Management, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " ISIN, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Impact Cost, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " CIN, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Listing Date, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Management, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Board of Directors, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Registered Office Address, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Registrars, BSE, BSEIndia'/>";
            strkeywords = strkeywords.replace("-", " ");
            strDescp = "<meta name='description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Board of Directors & Management, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Registered Office, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Registrars, Company Information '/> ";
            strDescp = strDescp.replace("-", " ");
            $('meta[name=description]').remove();
            $('meta[name=keywords]').remove();
            $(strkeywords).appendTo(document.head);
            $(strDescp).appendTo(document.head);

            strtwittertitle = "<meta name='twitter:title' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Board of Directors & Management, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Board of Directors & Management, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " ISIN, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Impact Cost, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " CIN, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Listing Date, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Management, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Board of Directors, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Registered Office Address, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Registrars, BSE, BSEIndia'/>";
            strtwittertitle = strtwittertitle.replace("-", " ");
            $('meta[name="twitter:title"]').remove();
            $(strtwittertitle).appendTo(document.head);

            strtwitterdes = "<meta name='twitter:description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Board of Directors & Management, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Registered Office, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Registrars, Company Information '/> ";
            strtwitterdes = strtwitterdes.replace("-", " ");
            $('meta[name="twitter:description"]').remove();
            $(strtwitterdes).appendTo(document.head);

            $('meta[name="twitter:url"]').remove();
            $("head").append("<meta name='twitter:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:url"]').remove();
            $("head").append("<meta property='og:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:title"]').remove();
            $("head").append("<meta property='og:title' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Board of Directors & Management, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Board of Directors & Management, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " ISIN, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Impact Cost, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " CIN, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Listing Date, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Management, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Board of Directors, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Registered Office Address, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Registrars, BSE, BSEIndia'/>");

            $('meta[property="og:description"]').remove();
            $("head").append("<meta property='og:description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Board of Directors & Management, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Registered Office, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Registrars, Company Information '/> ");
        }
        document.title = $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Board of Directors & Management, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Registered Office, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Registrars, Company Information | BSE";
    }
    $scope.fn_corpInfoTitle();
}]);

getquote.directive('noSpecialChar', function () {
    return {
        require: 'ngModel',
        restrict: 'A',
        link: function (scope, element, attrs, modelCtrl) {
            modelCtrl.$parsers.push(function (inputValue) {
                if (inputValue == null)
                    return ''
                cleanInputValue = inputValue.replace(/[^\w\s-@$.]/gi, '');
                if (cleanInputValue != inputValue) {
                    modelCtrl.$setViewValue(cleanInputValue);
                    modelCtrl.$render();
                }
                return cleanInputValue;
            });
        }
    }
});

//Controller Corporate Governance
getquote.constant('serviceurl28', {
    url_DropdownIndustry: 'binddropdown/w',
    url_CorpGovernance: 'CoroPriorPeriod/w',
    Url_CorpAnnexure1: 'Annexurepar1/w',
    Url_CorpAnnexure2: 'Annexurepar2/w',
    Url_CorpAnnexure3: 'Annexurepar3/w',
    Url_CorpAnnexHeader: 'GetMasterdetails/w',
    Url_SignaturAnx3: 'GetSignatoryPar/w',
    url_CropGovQuater: 'CGArchivewise/w',
    Url_CorpAnnexure4: 'Annexurepar4/w'
});
getquote.controller('CorpGovernanceController', ['serviceurl28', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function CorpGovernanceController(serviceurl28, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {



    $scope.loader = {
        CorpState: 'loading',
        Corpdelay: false,
        CorpState1: 'loading',
        Corpdelay1: false,
    };

    var querystr = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
    var FlagDur;
    var sc_code;
    var type;
    var Industry;
    var flag;
    var Masterid;
    var Shortname;
    var fullname;
    var QuaterName;

    $scope.getUrlParameter = function (param, dummyPath) {
        var sPageURL = dummyPath || window.location.search.substring(1),
            sURLVariables = sPageURL.split(/[&||?]/),
            res;
        for (var i = 0; i < sURLVariables.length; i += 1) {
            var paramName = sURLVariables[i],
                sParameterName = (paramName || '').split('=');
            if (sParameterName[0] === param) {
                res = sParameterName[1];
            }
        }
        return res;
    }
    if (querystr.indexOf('=') == -1) {
        var a = querystr.split('/')
        sc_code = a[6];
        Shortname = a[5];
        $scope.Shortname = Shortname;
        $scope.fullname = a[4];


        type = a[3];
        if (a.length > 7) {
            $scope.flag = a[8];
            $scope.masterid = a[7];
            $scope.QuaterName = a[9];

            Masterid = $scope.masterid;
            if (Masterid == "flag" || Masterid == null || Masterid == undefined || Masterid == "corporate-governance") {
                $scope.masterid = '';
            }
            else {
                $scope.masterid = a[7];
            }

        }
    }
    else {
        sc_code = $scope.getUrlParameter('scripcode', querystr);
        //flag = $scope.getUrlParameter('flag', querystr);
    }
    $rootScope.scripcode = sc_code;
    $scope.selperiod = $scope.flag;
    if ($scope.selperiod == null || $scope.selperiod == undefined || $scope.selperiod == "")
        $scope.selperiod = "1";
    $scope.selindustry = "ALL";

    $scope.fn_Corpgovnc = function () {
        $scope.loader.CorpState = 'loading';
        $scope.loader.Corpdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl28.url_CorpGovernance;
        $http({ url: url, method: "GET", params: { sc_code: $rootScope.scripcode, FlagDur: $scope.selperiod, Industry: $scope.selindustry } }).then(function (response) {
            $scope.CorpGovData = response.data;
            $scope.loader.CorpState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.Corpdelay = true;
                $scope.loader.CorpState = 'loading';
            }
        });
    }

    $scope.fn_Corpfillddl = function () {

        var url = mainapi.api_domainLIVE + serviceurl28.url_DropdownIndustry;
        $http({ url: url, method: "GET", params: { Flag: 1 } }).then(function successCallback(response) {
            $scope.ddldata = response.data;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
        });
    }

    $scope.fn_CorpfillIndus = function () {
        var url = mainapi.api_domainLIVE + serviceurl28.url_DropdownIndustry;
        $http({ url: url, method: "GET", params: { Flag: 2 } }).then(function successCallback(response) {

            $scope.ddldataIndustry = response.data;
            DropDownChnaged1();

            if ($scope.ddldataIndustry != undefined) {
                $scope.dropValue3 = "All";
            }
            // $scope.fn_Corpgovnc();
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
        });
    }

    $scope.fn_submitClick = function () {

        $scope.ddVal2 = $('#ddlAnnPeriod option:selected').val();
        $scope.ddVal3 = $('#ddlIndustry option:selected').val();

        var scriptcode = $("#scripsearchtxtbx").val();
        if ($scope.ddVal3 == "" || $scope.ddVal3 == "ALL") {
            $scope.ddVal3 = "ALL";
        }

        if (scriptcode == "") {
            $rootScope.scripcode = sc_code;
            scriptcode = sc_code;
        }

        $scope.loader.CorpState = 'loading';
        $scope.loader.Corpdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl28.url_CorpGovernance;
        $http({ url: url, method: "GET", params: { sc_code: scriptcode, FlagDur: $scope.ddVal2, Industry: $scope.ddVal3 } }).then(function (response) {
            $scope.CorpGovData = response.data;
            $scope.loader.CorpState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.Corpdelay = true;
                $scope.loader.CorpState = 'loading';
            }
        });
    };

    $scope.FnResetButton = function () {

        $scope.fn_CorpfillIndus();
        $scope.fn_Corpfillddl();
        $('#scripsearchtxtbx').val('');
        $scope.fn_Corpgovnc();
    }
    $scope.checknull = function (entnum) {
        if (entnum == null || entnum == undefined || entnum == "" || entnum == 0)
            return true;
        else
            return false;
    }
    $scope.trustAsHtml = function (string) {
        return $sce.trustAsHtml(string);
    };
    $scope.CorpAnnexure1 = function () {

        var Flag;
        $scope.loader.CorpState = 'loading';
        $scope.loader.Corpdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl28.Url_CorpAnnexure1;
        $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode, Masterid: $scope.masterid } }).then(function (response) {
            $scope.CorpAnnexureData = response.data;

            $scope.loader.CorpState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.Corpdelay = true;
                $scope.loader.CorpState = 'loading';
            }
        });
    }

    $scope.CorpAnnexure2 = function () {
        var Flag;
        $scope.loader.CorpState = 'loading';
        $scope.loader.Corpdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl28.Url_CorpAnnexure2;
        $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode, Masterid: $scope.masterid } }).then(function (response) {
            $scope.CorpAnnexureData2 = response.data;

            $scope.loader.CorpState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.Corpdelay = true;
                $scope.loader.CorpState = 'loading';
            }
        });
    };

    $scope.CorpAnnexure3 = function () {

        var Flag;
        $scope.loader.CorpState = 'loading';
        $scope.loader.Corpdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl28.Url_CorpAnnexure3;
        $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode, Masterid: $scope.masterid } }).then(function (response) {
            $scope.CorpAnnexureData3 = response.data;

            $scope.loader.CorpState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.Corpdelay = true;
                $scope.loader.CorpState = 'loading';
            }
        });
    };
    $scope.CorpAnnexure4 = function () {

        var Flag;
        $scope.loader.CorpState1 = 'loading';
        $scope.loader.Corpdelay1 = false;
        var url = mainapi.api_domainLIVE + serviceurl28.Url_CorpAnnexure4;
        $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode, Masterid: $scope.masterid } }).then(function (response) {
            $scope.CorpAnnexureData4 = response.data;

            $scope.loader.CorpState1 = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.Corpdelay1 = true;
                $scope.loader.CorpState1 = 'loading';
            }
        });
    };
    $scope.CorpAnnexureheaderData = function () {
        var Flag;
        $scope.loader.CorpState = 'loading';
        $scope.loader.Corpdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl28.Url_CorpAnnexHeader;
        $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode } }).then(function (response) {
            $scope.headerData = response.data;

            $scope.loader.CorpState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.Corpdelay = true;
                $scope.loader.CorpState = 'loading';
            }
        });
    }

    $scope.SignatureDetails = function () {
        $scope.loader.CorpState = 'loading';
        $scope.loader.Corpdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl28.Url_SignaturAnx3;
        $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode, Masterid: $scope.masterid } }).then(function (response) {
            $scope.SigData = response.data;

            $scope.loader.CorpState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.Corpdelay = true;
                $scope.loader.CorpState = 'loading';
            }
        });
    }

    $scope.fn_CorpGove_Quarter = function () {

        $scope.loader.CorpState = 'loading';
        $scope.loader.Corpdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl28.url_CropGovQuater;
        $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode } }).then(function (response) {
            $scope.CorpQuarter = response.data;

            $scope.loader.CorpState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.Corpdelay = true;
                $scope.loader.CorpState = 'loading';
            }
        });
    }

    $scope.fn_CorpGoveQueterTitle = function (qtrname) {
        var strtwittertitle = "";
        var strtwitterdes = "";
        var strkeywords = "";
        var strDescp = "";
        var strRawUrl = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
        var strRawUrl1 = $location.absUrl().replace(/[\\#,+()$~%"*<>{};]/g, '_');
        var strArray = strRawUrl.split('/');
        if (strArray != null && strArray.length > 5) {
            strkeywords = "<meta name='keywords' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Corporate Governance " + qtrname + " , " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Corporate Governance, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Composition of Board of Directors, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Composition of Committee, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Meeting of Board of Directors, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Meeting of Committees, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Related Party Transactions, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Affirmations, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Website Affirmations, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Annual Affirmation, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Affirmation, BSE, BSEIndia'/>";
            strkeywords = strkeywords.replace("-", " ");
            strDescp = "<meta name='description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Corporate Governance reports published on quarterly basis.Report gives details of Composition of Board of Directors and other committees'/> ";
            strDescp = strDescp.replace("-", " ");
            $('meta[name=description]').remove();
            $('meta[name=keywords]').remove();
            $(strkeywords).appendTo(document.head);
            $(strDescp).appendTo(document.head);

            strtwittertitle = "<meta name='twitter:title' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Corporate Governance " + qtrname + " , " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Corporate Governance, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Composition of Board of Directors, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Composition of Committee, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Meeting of Board of Directors, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Meeting of Committees, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Related Party Transactions, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Affirmations, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Website Affirmations, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Annual Affirmation, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Affirmation, BSE, BSEIndia'/>";
            strtwittertitle = strtwittertitle.replace("-", " ");
            $('meta[name="twitter:title"]').remove();
            $(strtwittertitle).appendTo(document.head);

            strtwitterdes = "<meta name='twitter:description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Corporate Governance reports published on quarterly basis.Report gives details of Composition of Board of Directors and other committees'/> ";
            strtwitterdes = strtwitterdes.replace("-", " ");
            $('meta[name="twitter:description"]').remove();
            $(strtwitterdes).appendTo(document.head);

            $('meta[name="twitter:url"]').remove();
            $("head").append("<meta name='twitter:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:url"]').remove();
            $("head").append("<meta property='og:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:title"]').remove();
            $("head").append("<meta property='og:title' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Corporate Governance " + qtrname + " , " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Corporate Governance, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Composition of Board of Directors, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Composition of Committee, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Meeting of Board of Directors, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Meeting of Committees, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Related Party Transactions, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Affirmations, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Website Affirmations, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Annual Affirmation, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Affirmation, BSE, BSEIndia'/>");

            $('meta[property="og:description"]').remove();
            $("head").append("<meta property='og:description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Corporate Governance reports published on quarterly basis.Report gives details of Composition of Board of Directors and other committees'/> ");
        }

        document.title = $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Board of Directors & Management, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Corporate Governance Reports, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Board of Directors & Other Committees | BSE";
    }
    $scope.fn_CorpGoveTitle = function () {
        var strtwittertitle = "";
        var strtwitterdes = "";
        var strkeywords = "";
        var strDescp = "";
        var strRawUrl = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
        var strRawUrl1 = $location.absUrl().replace(/[\\#,+()$~%"*<>{};]/g, '_');
        var strArray = strRawUrl.split('/');
        if (strArray != null && strArray.length > 5) {
            strkeywords = "<meta name='keywords' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Corporate Governance , " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Corporate Governance, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Composition of Board of Directors, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Composition of Committee, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Meeting of Board of Directors, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Meeting of Committees, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Related Party Transactions, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Affirmations, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Website Affirmations, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Annual Affirmation, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Affirmation, BSE, BSEIndia'/>";
            strkeywords = strkeywords.replace("-", " ");
            strDescp = "<meta name='description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Corporate Governance reports published on quarterly basis.Report gives details of Composition of Board of Directors and other committees'/> ";
            strDescp = strDescp.replace("-", " ");
            $('meta[name=description]').remove();
            $('meta[name=keywords]').remove();

            $(strkeywords).appendTo(document.head);
            $(strDescp).appendTo(document.head);

            strtwittertitle = "<meta name='twitter:title' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Corporate Governance , " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Corporate Governance, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Composition of Board of Directors, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Composition of Committee, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Meeting of Board of Directors, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Meeting of Committees, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Related Party Transactions, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Affirmations, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Website Affirmations, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Annual Affirmation, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Affirmation, BSE, BSEIndia'/>";
            strtwittertitle = strtwittertitle.replace("-", " ");
            $('meta[name="twitter:title"]').remove();
            $(strtwittertitle).appendTo(document.head);

            strtwitterdes = "<meta name='twitter:description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Corporate Governance reports published on quarterly basis.Report gives details of Composition of Board of Directors and other committees'/> ";
            strtwitterdes = strtwitterdes.replace("-", " ");
            $('meta[name="twitter:description"]').remove();
            $(strtwitterdes).appendTo(document.head);


            $('meta[name="twitter:url"]').remove();
            $("head").append("<meta name='twitter:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:url"]').remove();
            $("head").append("<meta property='og:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:title"]').remove();
            $("head").append("<meta property='og:title' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Corporate Governance , " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Corporate Governance, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Composition of Board of Directors, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Composition of Committee, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Meeting of Board of Directors, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Meeting of Committees, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Related Party Transactions, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Affirmations, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Website Affirmations, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Annual Affirmation, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Affirmation, BSE, BSEIndia'/>");

            $('meta[property="og:description"]').remove();
            $("head").append("<meta property='og:description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Corporate Governance reports published on quarterly basis.Report gives details of Composition of Board of Directors and other committees'/> ");
        }
        document.title = $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Board of Directors & Management, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Corporate Governance Reports, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Board of Directors & Other Committees | BSE";
    }
    if ($scope.QuaterName != null && $scope.QuaterName != "corporate-governance") {
        $scope.fn_CorpGoveQueterTitle($scope.QuaterName);
    }
    else {
        $scope.fn_CorpGoveTitle();
    }

    $scope.checkdebtscrip = function () {
        var deb = "/stock-share-price/debt-other/scripcode/" + $scope.scripcode + "/";
        if ($scope.scripcode >= 700000 && $scope.scripcode <= 999999) {
            return true;
        }
        else {
            return false;
        }

    };
}]);


//Controller Corporate Announcements
getquote.constant('serviceurl29', {
    url_corpann: 'AnnSubCategoryGetData/w',
    url_CateDataByNewsID: 'getDataByNewsid/w',
    url_subCateDataByNewsID: 'DDLSubCategoryData/w',
    url_corpxbrlann: 'XbrlAnnouncementCategory/w'
});

getquote.controller('corpannController', ['serviceurl29', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function corpannController(serviceurl29, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {

    $scope.loader = {
        CorpAnnState: 'loading',
        CorpAnndelay: false,

        CorpAnnFilterdelay: false,
        CorpAnnFilterState: 'loading',
    };

    var d = new Date();
    var month = d.getMonth() + 1;
    var day = d.getDate();
    var tooutput = (('' + day).length < 2 ? '0' : '') + day + '/' + (('' + month).length < 2 ? '0' : '') + month + '/' + d.getFullYear();

    var d1 = new Date(d.getFullYear(), d.getMonth() - 3, day);
    var fmonth = d1.getMonth() + 1;
    var fday = d1.getDate();
    var frmoutput = (('' + fday).length < 2 ? '0' : '') + fday + '/' + (('' + fmonth).length < 2 ? '0' : '') + fmonth + '/' + d1.getFullYear();

    var querystr = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');

    var scripcode, dur;
    if (querystr.length > 0) {
        if (querystr.indexOf('=') == -1) {
            var a = querystr.split('/')
            scripcode = a[6];
            type = a[5];
            $rootScope.scripcode = scripcode;
            $scope.FromDate = '';
            $scope.ToDate = '';

            $scope.AnnType = 'C';
            $scope.SerachBy = 'A';//if only scripcode pass then all data
            $scope.trIsDisplay = "1";
            $scope.FromDate = frmoutput;
            $scope.ToDate = tooutput;
            $scope.AnnsubmType = "0";
        }
        else {
            $scope.FromDate = frmoutput;
            $scope.ToDate = tooutput;

            $scope.AnnType = 'C';
            $scope.SerachBy = 'P';//if scripcode not pass then period data
            $scope.AnnsubmType = "0";
        }
    }
    else if (querystr.length > 0 && querystr.indexOf('anntype') != -1) {
        var a = querystr.split('?');
        if (a != undefined && a.length > 1) {
            var split = a[1].split('/');
            var anntype = split[1];
            $scope.AnnType = anntype;
            $scope.SerachBy = 'A';//if only scripcode pass then all data
            $scope.AnnsubmType = "0";
        }
        else {
            $scope.FromDate = frmoutput;
            $scope.ToDate = frmoutput;

            $scope.AnnType = 'C';
            $scope.SerachBy = 'P';//if scripcode not pass then period data
            $scope.AnnsubmType = "0";
        }
    }
    else {

        $scope.AnnType = 'C';
        $scope.FromDate = frmoutput;
        $scope.ToDate = tooutput;
        $scope.SerachBy = 'P';//if scripcode not pass then period data
        $scope.AnnsubmType = "0";
    }

    $scope.chktoDate = false;
    $scope.currentPage = 1;
    $scope.pagenumber = 0;
    $scope.chktoDate = false;
    $scope.loader.prevDisp = true;
    $scope.loader.NextDisp = true;
    $scope.scategory = '-1';
    //if ($scope.scategory == '-1' || $scope.scategory == undefined)
    //    $scope.scategory = '';


    if ($scope.category == '-1' || $scope.category == undefined)
        $scope.category = '-1';

    if ($rootScope.scripcode == null || $rootScope.scripcode == undefined) {
        $rootScope.scripcode = '';
    }

    if ($scope.FromDate == '' || $scope.FromDate == undefined)
        $scope.FromDates = '';
    else {
        $scope.FromDates = $scope.FromDate.split('/')[2] + $scope.FromDate.split('/')[1] + $scope.FromDate.split('/')[0];
    }

    if ($scope.ToDate == '' || $scope.ToDate == undefined)
        $scope.ToDates = '';
    else {
        $scope.ToDates = $scope.ToDate.split('/')[2] + $scope.ToDate.split('/')[1] + $scope.ToDate.split('/')[0];
    }

    $scope.fn_PrevPage = function () {

        if ($scope.currentPage == 1) {
            $('#idprev').hide();
        }
        else if ($scope.currentPage != 1) {
            $scope.currentPage = $scope.currentPage - 1;
            $scope.fn_CorpAnn($scope.currentPage);
        }
    }
    $scope.fn_NextPage = function () {
        if ($scope.currentPage < $scope.pagenumber) {
            $scope.currentPage = $scope.currentPage + 1;
            $scope.fn_CorpAnn($scope.currentPage);
        }

        if ($scope.currentPage == $scope.pagenumber) {
            $('#idnext').hide();
            $scope.loader.NextDisp = false;
        }
    }
    $scope.fn_fillddl = function () {
        $scope.scategory = '-1';
        $scope.category = $("#ddlPeriod :selected").text();
        if ($("#ddlPeriod :selected").text() == "--Select Category--") {
            $scope.category = "-1";
        }
        var url = mainapi.newapi_domain + serviceurl29.url_subCateDataByNewsID;
        $http({ url: url, method: "GET", params: { categoryname: $scope.category } }).then(function successCallback(response) {
            $scope.ddldata = response.data;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
        });
    }
    $scope.fn_CorpAnn = function (Pagenoa) {

        $scope.loader.CorpAnndelay = false;
        $scope.loader.CorpAnnState = 'loading';
        $scope.currentPage1 = Pagenoa;
        var url;
        var xbrlType = $scope.AnnsubmType;
        if (xbrlType == "1") {
            url = mainapi.newapi_domain + serviceurl29.url_corpxbrlann;
        }
        else {

            url = mainapi.newapi_domain + serviceurl29.url_corpann;
        }
        //var url = mainapi.newapi_domain + serviceurl29.url_corpann;
        $http({ url: url, method: "GET", params: { strScrip: $rootScope.scripcode, strCat: $scope.category, strPrevDate: $scope.FromDates, strToDate: $scope.ToDates, strSearch: $scope.SerachBy, strType: $scope.AnnType, pageno: $scope.currentPage1, subcategory: $scope.scategory } }).then(function successCallback(response) {
            $scope.CorpannData = (response.data);
            if ($scope.AnnType == 'EDDA') {
                $scope.totalItems = $scope.CorpannData.Table1[0]["ROWCNT"];
            }
            else {
                $scope.totalItems = $scope.CorpannData.Table1[0]["ROWCNT"];
            }
            $scope.loader.CorpAnnState = 'loaded';

            if ($scope.totalItems <= 50) {
                $scope.pagenumber = 1;
                $scope.loader.NextDisp = false;
                $scope.loader.prevDisp = false;
            }
            else {
                $scope.pagenumber = Math.ceil($scope.totalItems / 50);

                //if ($scope.currentPage >= $scope.pagenumber && $scope.pagenumber!=1) { 

                if ($scope.currentPage == $scope.pagenumber) { $scope.loader.NextDisp = false }

                else if ($scope.currentPage < $scope.pagenumber) { $scope.loader.NextDisp = true; }
                else {
                    $scope.loader.NextDisp = true;
                    $scope.loader.prevDisp = true;
                }
            }
        },

            function errorCallback(response) {
                $scope.status = response.status + "_" + response.statusText;
                if (response.status == (500 || 503)) {
                    $scope.loader.CorpAnndelay = true;
                    $scope.loader.CorpAnnState = 'loading';
                }
            }

        );
    }


    $scope.FnResetButton = function () {
        $("#ddlPeriod").val('-1');
        $("#ddlsubcat").val('-1');
        $("#ddlAnnType").val('C');
        $('#scripsearchtxtbx').val('');
        $scope.category = "-1";
        $scope.AnnType = "C";
        $scope.scategory = "-1";
        if ($scope.scategory != '-1' || $scope.scategory != undefined) {
            $scope.ddldata = '';
        }
        $scope.AnnsubmType = "0";
        $scope.fn_CorpAnn();
        $scope.FromDate = frmoutput;
        $scope.ToDate = tooutput;
    }
    $scope.onchange = function () {
        $scope.AnnType = $('#ddlAnnType option:selected').val();
        $scope.currentPage = 1;

    }

    $scope.fn_CorpAnnFilter = function (frmDate, ToDate) {
        $scope.AnnType = $('#ddlAnnType option:selected').val();
        $scope.currentPage = 1;
        $scope.pagenumber = 0;
        var url;
        var xbrlType = $scope.AnnsubmType;
        if (xbrlType == "1") {
            url = mainapi.newapi_domain + serviceurl29.url_corpxbrlann;
        }
        else {

            url = mainapi.newapi_domain + serviceurl29.url_corpann;
        }
        //   var url = mainapi.api_domainLIVE + serviceurl29.url_corpann;
        var scripcode = $rootScope.scripcode == '' ? '' : $rootScope.scripcode;
        if (scripcode.length == 0) {
            var querystr = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
            if (querystr.indexOf('=') == -1) {
                var a = querystr.split('/')
                scripcode = a[6];
                type = a[5];
                $rootScope.scripcode = scripcode;
            }
        }
        $http({ url: url, method: "GET", params: { strScrip: scripcode, strCat: $scope.category, strPrevDate: frmDate, strToDate: ToDate, strSearch: $scope.SerachBy, strType: $scope.AnnType, pageno: $scope.currentPage, subcategory: $scope.scategory } }).then(function successCallback(response) {
            $scope.CorpannData = (response.data);
            // console.log("2" + response.data);
            if ($scope.AnnType == 'EDDA') {
                $scope.totalItems = $scope.CorpannData.Table1[0]["ROWCNT"];
            }
            else {
                $scope.totalItems = $scope.CorpannData.Table1[0]["ROWCNT"];
            }
            $scope.loader.CorpAnnState = 'loaded';

            if ($scope.totalItems <= 50) {
                $scope.pagenumber = 1;
                $scope.loader.NextDisp = false;
                $scope.loader.prevDisp = false;

            }
            else {
                $scope.pagenumber = Math.ceil($scope.totalItems / 50);

                if ($scope.currentPage == $scope.pagenumber) { $scope.loader.NextDisp = false }

                else if ($scope.currentPage < $scope.pagenumber) {

                    $scope.loader.NextDisp = true;

                }
                else {
                    $scope.loader.NextDisp = true;
                    $scope.loader.prevDisp = true;


                }
            }
        },
            function errorCallback(response) {
                $scope.status = response.status + "_" + response.statusText;
                if (response.status == (500 || 503)) {
                    $scope.loader.CorpAnnFilterdelay = true;
                    $scope.loader.CorpAnnState = 'loading';
                }
            }

        );
    }
    $scope.fn_dwnldxbrl = function (filename, scripcode) {
        var url = "/Msource/90D/CorpXbrlGen.aspx?Bsenewid=" + filename + "&Scripcode=" + scripcode;
        $window.open(url, "_blank");
    }


    $scope.fnchkSearchValid = function () {

        if ($scope.SerachBy == 'D') {

            $scope.FromDate == ''
            $scope.chkfrmDate = false;
            $scope.ToDate == ''
            $scope.chktoDate = true;
        }
        else if ($scope.SerachBy == 'P') {
            $scope.FromDate == ''
            $scope.chkfrmDate = true;
            $scope.ToDate == ''
            $scope.chktoDate = true;
        }
        else if ($scope.SerachBy == 'A') {
            $scope.FromDate == ''
            $scope.chkfrmDate = false;
            $scope.ToDate == ''
            $scope.chktoDate = false;
        }
    }

    $scope.fnAnnById = function (newsid) {

        $scope.CorpannDatas = JSON.parse(JSON.stringify($scope.CorpannData.Table));
        var comArr = eval($scope.CorpannDatas);
        for (var i = 0; i < comArr.length; i++) {
            if (comArr[i].NEWSID === newsid) {
                index = i;
                break;
            }
        }
        $scope.CorpannDataByNewsId = JSON.parse(JSON.stringify($scope.CorpannDatas.splice(index, 1)));
        // console.log($scope.CorpannDataByNewsId);
    }
    $scope.fn_downloadPdf = function (newsid) {
        $scope.CorpannDatas = JSON.parse(JSON.stringify($scope.CorpannData.Table));
        var comArr = eval($scope.CorpannDatas);
        for (var i = 0; i < comArr.length; i++) {
            if (comArr[i].NEWSID === newsid) {
                index = i;
                break;
            }
        }
        $scope.CorpannDataByNewsId = JSON.parse(JSON.stringify($scope.CorpannDatas.splice(index, 1)));
        var splitedDateTime = ($scope.CorpannDataByNewsId[0].NEWS_DT).toString().split('-');
        var path = splitedDateTime[0] + "/" + splitedDateTime[1] + "/";
        var year = splitedDateTime[0];
        var month = (splitedDateTime[1] < 10 ? splitedDateTime[1].substr(1) : splitedDateTime[1]);
        var url = "/xml-data/corpfiling/CorpAttachment/" + year + "/" + month + "/" + $scope.CorpannDataByNewsId[0].ATTACHMENTNAME;
        $window.open(url, "_blank");
    }

    $scope.fn_submit = function () {

        $scope.loader.CorpAnnFilterdelay = false;
        $scope.loader.CorpAnnState = 'loading';
        var querystr = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};&=]/g, '/');
        if ($scope.FromDate != '') {
            if ($scope.ToDate == '') {
                $scope.loader.CorpAnnState = 'loaded';
                alert('Please Enter To Date');
                return false;
            }
            else if ($scope.FromDate != '' && $scope.ToDate != '') {
                $scope.FromDates = $scope.FromDate.split('/')[1] + '/' + $scope.FromDate.split('/')[0] + '/' + $scope.FromDate.split('/')[2];
                $scope.ToDates = $scope.ToDate.split('/')[1] + '/' + $scope.ToDate.split('/')[0] + '/' + $scope.ToDate.split('/')[2];
                var fromdate = new Date($scope.FromDates);
                var toDate = new Date($scope.ToDates);


                if (fromdate > toDate) {
                    $scope.loader.CorpAnnState = 'loaded';
                    alert('From date should not be greater than to date');
                    return false;
                }
                else {
                    const oneDay = 24 * 60 * 60 * 1000; // hours*minutes*seconds*milliseconds
                    const firstDate = new Date($scope.FromDates);
                    const secondDate = new Date($scope.ToDates);
                    const diffDays = Math.round(Math.abs((firstDate - secondDate) / oneDay));

                    if (diffDays > 365) {
                        $scope.loader.CorpAnnState = 'loaded';
                        alert('Period should not be more than 12 months');
                        return false;
                    }

                    if ($scope.FromDates == $scope.ToDates && $scope.FromDates.length > 0 && $scope.ToDates.length > 0) {
                        if ($scope.FromDate) {
                            $scope.FromDates = $scope.FromDate.split('/')[2] + $scope.FromDate.split('/')[1] + $scope.FromDate.split('/')[0];
                        }
                        else
                            $scope.FromDates = '';

                        if ($scope.ToDate) {
                            $scope.ToDates = $scope.ToDate.split('/')[2] + $scope.ToDate.split('/')[1] + $scope.ToDate.split('/')[0];
                        }
                        else
                            $scope.ToDates = '';
                        $scope.SerachBy = 'P'
                        $scope.fn_CorpAnnFilter($scope.FromDates, $scope.ToDates);//if all validtion complete then call again filter function
                    }
                    else if ((querystr.length > 0 && $rootScope.scripcode.length > 0) || ($scope.category != '-1')) {

                        if ($scope.FromDate) {
                            $scope.FromDates = $scope.FromDate.split('/')[2] + $scope.FromDate.split('/')[1] + $scope.FromDate.split('/')[0];
                        }
                        else
                            $scope.FromDates = '';

                        if ($scope.ToDate) {
                            $scope.ToDates = $scope.ToDate.split('/')[2] + $scope.ToDate.split('/')[1] + $scope.ToDate.split('/')[0];
                        }
                        else
                            $scope.ToDates = '';
                        $scope.SerachBy = 'P';

                        $scope.fn_CorpAnnFilter($scope.FromDates, $scope.ToDates);//if all validtion complete then call again filter function
                    }
                    else {
                        $scope.loader.CorpAnnState = 'loaded';
                        alert('Please Select Either Security Name or Category ');
                        return false;

                    }
                }
            }

        }
        else if ($scope.ToDate != '' && $scope.FromDate == '') {
            $scope.loader.CorpAnnState = 'loaded';
            alert('Please Enter From Date');
            return false;
        }
        else if ($scope.ToDate == '' && $scope.FromDate == '') {
            $scope.loader.CorpAnnState = 'loaded';
            alert('Please Enter From Date and To Date');
            return false;

        }

    }
    $scope.fn_CorpAnnTitle = function () {
        var strtwittertitle = "";
        var strtwitterdes = "";
        var strkeywords = "";
        var strDescp = "";
        var strRawUrl = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
        var strRawUrl1 = $location.absUrl().replace(/[\\#,+()$~%"*<>{};]/g, '_');
        var strArray = strRawUrl.split('/');
        if (strArray != null && strArray.length > 5) {
            strkeywords = "<meta name='keywords' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " News, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Announcements, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  Updates, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " News, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Announcements, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  Updates, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Latest News, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Latest News,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Latest Announcements, BSE, BSEIndia'/>";
            strkeywords = strkeywords.replace("-", " ");
            strDescp = "<meta name='description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " latest corporate news & announcements, Be updated on the live and latest happenings in " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " with the fastest & most reliable source '/> ";
            strDescp = strDescp.replace("-", " ");
            $('meta[name=description]').remove();
            $('meta[name=keywords]').remove();

            $(strkeywords).appendTo(document.head);
            $(strDescp).appendTo(document.head);

            strtwittertitle = "<meta name='twitter:title' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " News, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Announcements, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  Updates, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " News, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Announcements, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  Updates, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Latest News, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Latest News,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Latest Announcements, BSE, BSEIndia'/>";
            strtwittertitle = strtwittertitle.replace("-", " ");
            $('meta[name="twitter:title"]').remove();
            $(strtwittertitle).appendTo(document.head);

            strtwitterdes = "<meta name='twitter:description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " latest corporate news & announcements, Be updated on the live and latest happenings in " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " with the fastest & most reliable source '/> ";
            strtwitterdes = strtwitterdes.replace("-", " ");
            $('meta[name="twitter:description"]').remove();
            $(strtwitterdes).appendTo(document.head);

            $('meta[name="twitter:url"]').remove();
            $("head").append("<meta name='twitter:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:url"]').remove();
            $("head").append("<meta property='og:url' content=" + strRawUrl1 + ">");

            $('meta[property="og:title"]').remove();
            $("head").append("<meta property='og:title' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " News, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Announcements, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  Updates, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " News, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Announcements, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "  Updates, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Latest News, " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Latest News,  " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + " Latest Announcements, BSE, BSEIndia'/>");

            $('meta[property="og:description"]').remove();
            $("head").append("<meta property='og:description' content= '" + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " latest corporate news & announcements, Be updated on the live and latest happenings in " + $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " with the fastest & most reliable source '/> ");
        }
        document.title = $rootScope.camelize(strArray[4].replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ").replace("-", " ")) + " Latest Corporate Announcements, " + $rootScope.camelize(strArray[5].replace("-", " ").replace("-", " ")) + "Latest Company News, |BSE";
    }
    $scope.fn_CorpAnnTitle();

    $scope.trustAsHtml = function (string) {
        return $sce.trustAsHtml(string);
    };

    $scope.checknotnull = function (entnum) {
        if (entnum == null || entnum == undefined || entnum == "" || entnum == 0)
            return false;
        else

            return true;
    }


    $scope.showtd = true;
    $scope.hidetd = false;

    $scope.moreclick = function (newsid, idm, idr, flag) {

        $scope.CorpannDatas = JSON.parse(JSON.stringify($scope.CorpannData.Table));
        var comArr = eval($scope.CorpannDatas);
        for (var i = 0; i < comArr.length; i++) {
            if (comArr[i].NEWSID === newsid) {
                $scope.newsid = idm + comArr[i].NEWSID;
                $scope.moreid = idr + comArr[i].NEWSID;
                index = i;
                openID($scope.newsid, $scope.moreid, flag);
                break;
            }

        }
        $scope.CorpannDataByNewsId = JSON.parse(JSON.stringify($scope.CorpannDatas.splice(index, 1)));
        $scope.moreid = sv + $scope.CorpannDataByNewsId[0].NEWSID;

    }
}]);

//Controller MFUPSI Announcements

getquote.constant('serviceur130', {
    url_upsiquarterdata: 'MFPITupsidata/w',
    url_MFPITTradeplan: 'MFPITtradingplandata/w',
    url_MFPIToffmarket: 'MFPIToffmarkettransdata/w',
    url_MFPITeventdisdata: 'MFPITeventdisdata/w',
    url_MFPITquarterdata: 'MFPITquarterdata/w',
    url_MFPITcorpinfodata: 'MFPITcorpinfo/w'
});
getquote.controller('eqmfupsiController', ['serviceur130', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqbrsrController(serviceur130, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {


    $scope.loader = {
        SHState: 'loading',
        SHdelay: false,
    };

    var querystr = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
    var flag;
    var scripcode;
    var type;
    var qtrid;
    $scope.getUrlParameter = function (param, dummyPath) {
        var sPageURL = dummyPath || window.location.search.substring(1),
            sURLVariables = sPageURL.split(/[&||?]/),
            res;
        for (var i = 0; i < sURLVariables.length; i += 1) {
            var paramName = sURLVariables[i],
                sParameterName = (paramName || '').split('=');
            if (sParameterName[0] === param) {
                res = sParameterName[1];
            }
        }
        return res;
    }
    if (querystr.indexOf('=') == -1) {
        var a = querystr.split('/')
        scripcode = a[6];
        type = a[5];
        if (a.length > 7 && a[7] == "upsi") {
        }
        if (a.length > 7 && a[7] == "off-market-transaction") {
        }
        if (a.length > 7 && a[7] == "trading-plan") {
        }
        if (a.length > 7 && a[7] == "quarterly-disclosures") {
        }
        if (a.length > 7 && a[7] == "event-based-disclosures") {
        }
    }
    else {
        scripcode = $scope.getUrlParameter('scripcode', querystr);
        //flag = $scope.getUrlParameter('flag', querystr);
    }
    $rootScope.scripcode = scripcode;
    $scope.selperiod = 0;

    $scope.checknull = function (entnum) {
        if (entnum == null || entnum == undefined || entnum == "" || entnum == 0)
            return true;
        else
            return false;
    }



    $scope.fn_upsi_Quarter = function () {
        $scope.loader.SHState = 'loading';
        $scope.loader.SHdelay = false;
        var url = mainapi.api_domainLIVE + serviceur130.url_upsiquarterdata;
        var urlF = $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode } }).then(function (response) {
            $scope.upsiQuarter = response.data;
            $scope.loader.SHState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHdelay = true;
                $scope.loader.SHState = 'loading';
            }
        });
    };

    $scope.fn_mfeventdisdata = function () {
        $scope.loader.SHState = 'loading';
        $scope.loader.SHdelay = false;
        var url = mainapi.api_domainLIVE + serviceur130.url_MFPITeventdisdata;
        var urlF = $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode } }).then(function (response) {
            $scope.eventdisdata = response.data;
            $scope.loader.SHState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHdelay = true;
                $scope.loader.SHState = 'loading';
            }
        });
    };

    $scope.fn_mfquarterdata = function () {
        $scope.loader.SHState = 'loading';
        $scope.loader.SHdelay = false;
        var url = mainapi.api_domainLIVE + serviceur130.url_MFPITquarterdata;
        var urlF = $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode } }).then(function (response) {
            $scope.quarterdata = response.data;
            $scope.loader.SHState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHdelay = true;
                $scope.loader.SHState = 'loading';
            }
        });
    };
    $scope.fn_mftradeplan = function () {
        $scope.loader.SHState = 'loading';
        $scope.loader.SHdelay = false;
        var url = mainapi.api_domainLIVE + serviceur130.url_MFPITTradeplan;
        var urlF = $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode } }).then(function (response) {
            $scope.tradeplanrecord = response.data;
            $scope.loader.SHState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHdelay = true;
                $scope.loader.SHState = 'loading';
            }
        });
    };
    $scope.fn_mfoffmarket = function () {
        $scope.loader.SHState = 'loading';
        $scope.loader.SHdelay = false;
        var url = mainapi.api_domainLIVE + serviceur130.url_MFPIToffmarket;
        var urlF = $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode } }).then(function (response) {
            $scope.offmarketrecord = response.data;
            $scope.loader.SHState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHdelay = true;
                $scope.loader.SHState = 'loading';
            }
        });
    };

    $scope.fn_mfcorpinfo = function () {
        $scope.loader.SHState = 'loading';
        $scope.loader.SHdelay = false;
        var url = mainapi.api_domainLIVE + serviceur130.url_MFPITcorpinfodata;
        var urlF = $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode } }).then(function (response) {
            $scope.PITcorpinfodata = response.data;
            $scope.loader.SHState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHdelay = true;
                $scope.loader.SHState = 'loading';
            }
        });
    };
}]);
//Controller for PIT
getquote.constant('serviceurl131', {
    url_sddpitdata: 'sddpit/w',
    url_sddpit_Downloadcsv: 'SDDPIT_Download/w'
});
getquote.controller('eqsddphase3_controller', ['serviceurl131', '$scope', '$http', '$timeout', '$injector', '$window', '$location', '$rootScope', 'mainapi', '$sce', function eqsddphase3_controller(serviceurl131, $scope, $http, $timeout, $injector, $window, $location, $rootScope, mainapi, $sce) {

    $scope.FromDate = '';
    $scope.ToDate = '';
    $scope.totalItems = 0;
    $scope.currentPage = 1;
    $scope.itemsPerPage = 25;
    $scope.maxSize = 5;


    $scope.loader = {
        gloading: 'loading',
        delay: false,
    };
    $scope.fn_sddpit = function () {

        $scope.loader.gloading = 'loading';
        $scope.loader.delay = false;
        var url = mainapi.newapi_domain + serviceurl131.url_sddpitdata;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, fromdt: $scope.FromDate, todt: $scope.ToDate } }).then(function successCallback(response) {

            $scope.ContinualDisclosurepit = (response.data);
            $scope.loader.gloading = 'loaded';
            $scope.loader.delay = false;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.delay = true;
                $scope.loader.gloading = 'loading';
            }
        });
    }

    $scope.fn_sddpit_Downloadcsv = function () {

        $scope.loader.gloading = 'loading';
        $scope.loader.delay = false;
        var url = mainapi.newapi_domain + serviceurl131.url_sddpit_Downloadcsv;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, fromdt: $scope.FromDate, todt: $scope.ToDate } }).then(function successCallback(response) {
            window.open(url, "_self");
            $scope.ContinualDisclosurepit = (response.data);
            $scope.loader.gloading = 'loaded';
            $scope.loader.delay = false;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.delay = true;
                $scope.loader.gloading = 'loading';
            }
        });
    }

    $scope.fn_submit = function () {

        $scope.loader.gloading = 'loading';
        $scope.loader.delay = false;
        if ($scope.FromDate != "" || $scope.ToDate != "") {

            if ($scope.FromDate == "") {
                alert('Please enter  from date');
                return false;
            }
            if ($scope.ToDate == "") {
                alert('Please enter  to date');
                return false;
            }
            if ($scope.FromDate != '' && $scope.ToDates != '') {
                $scope.FromDates = $scope.FromDate.split('/')[1] + '/' + $scope.FromDate.split('/')[0] + '/' + $scope.FromDate.split('/')[2];
                $scope.ToDates = $scope.ToDate.split('/')[1] + '/' + $scope.ToDate.split('/')[0] + '/' + $scope.ToDate.split('/')[2];
                var fromdate = new Date($scope.FromDates);
                var toDate = new Date($scope.ToDates);

                if (fromdate > toDate) {

                    alert('From date should not be greater than to date');
                    return false;
                }
                else {

                    if ($scope.FromDates != '' && $scope.ToDates != '') {
                        if ($scope.FromDate) {
                            $scope.FromDates = $scope.FromDate.split('/')[2] + $scope.FromDate.split('/')[1] + $scope.FromDate.split('/')[0];
                        }
                        else
                            $scope.FromDates = '';

                        if ($scope.ToDate) {
                            $scope.ToDates = $scope.ToDate.split('/')[2] + $scope.ToDate.split('/')[1] + $scope.ToDate.split('/')[0];
                        }
                        else
                            $scope.ToDates = '';


                        var url = mainapi.newapi_domain + serviceurl131.url_sddpitdata;
                        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, fromdt: $scope.FromDates, todt: $scope.ToDates } }).then(function successCallback(response) {
                            $scope.ContinualDisclosurepit = (response.data);
                            $scope.loader.gloading = 'loaded';
                            $scope.loader.delay = false;
                        }, function errorCallback(response) {
                            $scope.status = response.status + "_" + response.statusText;
                            if (response.status == (500 || 503)) {
                                $scope.loader.delay = true;
                                $scope.loader.gloading = 'loading';
                            }
                        });

                    }
                }
            }

        }
    }



    $scope.fn_downloadpitcsv = function () {
        var fdt, tdt
        if ($scope.FromDates == undefined) {
            fdt = "";
        }
        else {
            fdt = $scope.FromDates;
        }
        if ($scope.ToDates == undefined) {
            tdt = "";
        }
        else {
            tdt = $scope.ToDates;
        }
        var url = mainapi.newapi_domain + serviceurl131.url_sddpit_Downloadcsv + "?scripcode=" + $scope.scripcode + "&fromdt=" + fdt + "&todt=" + tdt;
        return url;


    }

    $scope.recallFunction = function () {
        $timeout(function () {
            if ($scope.loader.delay == true) { $scope.fn_sddpit(); }
            $scope.recallFunction();
        }, 20000)
    };
    $scope.recallFunction();
}]);

//For intermediaries DT  and CRA
getquote.constant('serviceurl132', {
    url_disontermedt: 'DisclosureDT/w',
    url_disontermecra: 'DisclosureCRA/w'
});
getquote.controller('disintermeDTCRA_controller', ['serviceurl132', '$scope', '$http', '$timeout', '$injector', '$window', '$location', '$rootScope', 'mainapi', '$sce', function disintermeDTCRA_controller(serviceurl132, $scope, $http, $timeout, $injector, $window, $location, $rootScope, mainapi, $sce) {

    $scope.FromDate = '';
    $scope.ToDate = '';
    $scope.totalItems = 0;
    $scope.currentPage = 1;
    $scope.itemsPerPage = 25;
    $scope.maxSize = 5;


    $scope.loader = {
        gloading: 'loading',
        delay: false,
    };
    $scope.fn_disclosintermedt = function () {

        $scope.loader.gloading = 'loading';
        $scope.loader.delay = false;
        var url = mainapi.newapi_domain + serviceurl132.url_disontermedt;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, fromdt: $scope.FromDate, todt: $scope.ToDate } }).then(function successCallback(response) {

            $scope.disclosintermedt = (response.data);
            $scope.loader.gloading = 'loaded';
            $scope.loader.delay = false;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.delay = true;
                $scope.loader.gloading = 'loading';
            }
        });
    }
    $scope.fn_viewdt = function (dtd) {

        $scope.loader.gloading = 'loading';
        $scope.loader.delay = false;
        var url = mainapi.newapi_domain + serviceurl132.url_disontermedt;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, fromdt: $scope.FromDate, todt: $scope.ToDate, DTDIS: dtd } }).then(function successCallback(response) {

            $scope.disclosintermedtsd = (response.data);
            $scope.loader.gloading = 'loaded';
            $scope.loader.delay = false;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.delay = true;
                $scope.loader.gloading = 'loading';
            }
        });
    }
    $scope.fn_disclosintermecra = function () {

        $scope.loader.gloading = 'loading';
        $scope.loader.delay = false;
        var url = mainapi.newapi_domain + serviceurl132.url_disontermecra;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, fromdt: $scope.FromDate, todt: $scope.ToDate } }).then(function successCallback(response) {

            $scope.disclosintermecra = (response.data);
            $scope.loader.gloading = 'loaded';
            $scope.loader.delay = false;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.delay = true;
                $scope.loader.gloading = 'loading';
            }
        });
    }

    $scope.fn_viewcra = function (crad) {

        $scope.loader.gloading = 'loading';
        $scope.loader.delay = false;
        var url = mainapi.newapi_domain + serviceurl132.url_disontermecra;
        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, fromdt: $scope.FromDate, todt: $scope.ToDate, CRADIS: crad } }).then(function successCallback(response) {

            $scope.disclosintermedtcra = (response.data);
            $scope.loader.gloading = 'loaded';
            $scope.loader.delay = false;
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.delay = true;
                $scope.loader.gloading = 'loading';
            }
        });
    }
    $scope.fn_submit_dcra = function () {

        $scope.loader.gloading = 'loading';
        $scope.loader.delay = false;
        if ($scope.FromDate != "" || $scope.ToDate != "") {

            if ($scope.FromDate == "") {
                alert('Please enter  from date');
                return false;
            }
            if ($scope.ToDate == "") {
                alert('Please enter  to date');
                return false;
            }
            if ($scope.FromDate != '' && $scope.ToDates != '') {
                $scope.FromDates = $scope.FromDate.split('/')[1] + '/' + $scope.FromDate.split('/')[0] + '/' + $scope.FromDate.split('/')[2];
                $scope.ToDates = $scope.ToDate.split('/')[1] + '/' + $scope.ToDate.split('/')[0] + '/' + $scope.ToDate.split('/')[2];
                var fromdate = new Date($scope.FromDates);
                var toDate = new Date($scope.ToDates);

                if (fromdate > toDate) {

                    alert('From date should not be greater than to date');
                    return false;
                }
                else {

                    if ($scope.FromDates != '' && $scope.ToDates != '') {
                        if ($scope.FromDate) {
                            $scope.FromDate = $scope.FromDate.split('/')[2] + $scope.FromDate.split('/')[1] + $scope.FromDate.split('/')[0];
                        }
                        else
                            $scope.FromDate = '';

                        if ($scope.ToDate) {
                            $scope.ToDate = $scope.ToDate.split('/')[2] + $scope.ToDate.split('/')[1] + $scope.ToDate.split('/')[0];
                        }
                        else
                            $scope.ToDate = '';

                        $scope.fn_disclosintermecra();

                    }
                }
            }

        }
    }
    $scope.fn_submit_dt = function () {

        $scope.loader.gloading = 'loading';
        $scope.loader.delay = false;
        if ($scope.FromDate != "" || $scope.ToDate != "") {

            if ($scope.FromDate == "") {
                alert('Please enter  from date');
                return false;
            }
            if ($scope.ToDate == "") {
                alert('Please enter  to date');
                return false;
            }
            if ($scope.FromDate != '' && $scope.ToDates != '') {
                $scope.FromDates = $scope.FromDate.split('/')[1] + '/' + $scope.FromDate.split('/')[0] + '/' + $scope.FromDate.split('/')[2];
                $scope.ToDates = $scope.ToDate.split('/')[1] + '/' + $scope.ToDate.split('/')[0] + '/' + $scope.ToDate.split('/')[2];
                var fromdate = new Date($scope.FromDates);
                var toDate = new Date($scope.ToDates);

                if (fromdate > toDate) {

                    alert('From date should not be greater than to date');
                    return false;
                }
                else {

                    if ($scope.FromDates != '' && $scope.ToDates != '') {
                        if ($scope.FromDate) {
                            $scope.FromDate = $scope.FromDate.split('/')[2] + $scope.FromDate.split('/')[1] + $scope.FromDate.split('/')[0];
                        }
                        else
                            $scope.FromDate = '';

                        if ($scope.ToDate) {
                            $scope.ToDate = $scope.ToDate.split('/')[2] + $scope.ToDate.split('/')[1] + $scope.ToDate.split('/')[0];
                        }
                        else
                            $scope.ToDate = '';

                        $scope.fn_disclosintermedt();
                        //var url = 'http://localhost:56980/api/' + serviceurl132.url_disontermedt;
                        //$http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, fromdt: $scope.FromDate, todt: $scope.ToDate } }).then(function successCallback(response) {

                        //    $scope.disclosintermedt = (response.data);
                        //    $scope.loader.gloading = 'loaded';
                        //    $scope.loader.delay = false;
                        //}, function errorCallback(response) {
                        //    $scope.status = response.status + "_" + response.statusText;
                        //    if (response.status == (500 || 503)) {
                        //        $scope.loader.delay = true;
                        //        $scope.loader.gloading = 'loading';
                        //    }
                        //});

                    }
                }
            }

        }
    }
    $scope.recallFunction = function () {
        $timeout(function () {
            if ($scope.loader.delay == true) { $scope.fn_sddpit(); }
            $scope.recallFunction();
        }, 20000)
    };
    $scope.recallFunction();
}]);

//For intermediaries PIT Trading Plan

getquote.constant('serviceurl133', {

    url_GetPITTrading: 'GetPITTradingplan/w',

    url_PITdownloadcsv: 'DownloadPITTradingplancsv/w',

});

getquote.controller('PITTradingPlan_controller', ['serviceurl133', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function PITTradingPlan_controller(serviceurl133, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {







    $scope.loader = {

        STOCKState: 'loading',

        STOCKdelay: false,

    };



    $scope.FromDate = '';

    $scope.ToDate = '';

    $scope.totalItems = 0;

    $scope.currentPage = 1;

    $scope.itemsPerPage = 25;

    $scope.maxSize = 5; //Number of pager buttons to show



    $scope.fn_pittrad = function () {

        $scope.loader.STOCKState = 'loading';

        $scope.loader.STOCKdelay = false;

        var url = mainapi.api_domainLIVE + serviceurl133.url_GetPITTrading;

        $http({ url: url, method: "GET", params: { scripcode: $scope.scripcode, fromdt: $scope.FromDate, todt: $scope.ToDate } }).then(function successCallback(response) {

            $scope.PITradingresult = response.data;

            $scope.loader.STOCKState = 'loaded';

            $scope.totalItems = $scope.PITradingresult.Table.length;

            $scope.currentPage = 1;

        }, function errorCallback(response) {

            $scope.status = response.status + "_" + response.statusText;

            if (response.status == (500 || 503)) {

                $scope.loader.STOCKdelay = true;

                $scope.loader.STOCKState = 'loading';

            }

        });

    }

    $scope.fn_PITTradFilter = function (scripcode, frmDate, ToDate) {

        $scope.loader.STOCKState = 'loading';

        $scope.loader.STOCKdelay = false;

        var url = mainapi.api_domainLIVE + serviceurl133.url_GetPITTrading;

        $http({ url: url, method: "GET", params: { scripcode: scripcode, fromdt: frmDate, todt: ToDate } }).then(function successCallback(response) {



            $scope.PITradingresult = (response.data);

            $scope.loader.STOCKState = 'loaded';

            $scope.loader.STOCKdelay = false;

        }, function errorCallback(response) {

            $scope.status = response.status + "_" + response.statusText;

            if (response.status == (500 || 503 || 403)) {

                $scope.loader.delay = true;

                $scope.loader.gloading = 'loading';

            }

        });

    }

    $scope.fn_submitPTP = function () {

        if ($scope.FromDate != "" && $scope.ToDate != "") {

            var fmdt = new Date($scope.FromDate.split('/')[2], $scope.FromDate.split('/')[1] - 1, $scope.FromDate.split('/')[0]);

            var todt = new Date($scope.ToDate.split('/')[2], $scope.ToDate.split('/')[1] - 1, $scope.ToDate.split('/')[0]);

            if (fmdt > todt) {

                alert('From date should be less than To date'); return;

            }

            else {

                if ($scope.FromDate) {

                    $scope.FromDates = $scope.FromDate.split('/')[2] + '-' + $scope.FromDate.split('/')[1] + '-' + $scope.FromDate.split('/')[0];

                }

                else

                    $scope.FromDates = '';



                if ($scope.ToDate) {

                    $scope.ToDates = $scope.ToDate.split('/')[2] + '-' + $scope.ToDate.split('/')[1] + '-' + $scope.ToDate.split('/')[0];

                }

                else

                    $scope.ToDates = '';



                $scope.fn_PITTradFilter($scope.scripcode, $scope.FromDates, $scope.ToDates);



            }

        }

        else if ($scope.FromDate != "" && $scope.ToDate == "") {

            alert('Please enter From Date');

        }

        else if ($scope.FromDate == "" && $scope.ToDate != "") {

            alert('Please enter To Date');

        }

    }



    $scope.fn_downloadPITTPcsv = function () {

        if ($scope.FromDate) {

            $scope.FromDates = $scope.FromDate.split('/')[2] + '-' + $scope.FromDate.split('/')[1] + '-' + $scope.FromDate.split('/')[0];

        }

        else

            $scope.FromDates = '';



        if ($scope.ToDate) {

            $scope.ToDates = $scope.ToDate.split('/')[2] + '-' + $scope.ToDate.split('/')[1] + '-' + $scope.ToDate.split('/')[0];

        }

        else

            $scope.ToDates = '';

        var url = mainapi.api_domainLIVE + serviceurl133.url_PITdownloadcsv + "?scripcode=" + $scope.scripcode + "&fromdt=" + $scope.FromDates + "&todt=" + $scope.ToDates;

        return url;



    }

    $scope.fn_PITTradereset = function () {





        $("#txtToDt").val('');

        $("#txtFromDt").val('');

        $scope.FromDates = '';

        $scope.ToDates = '';

        $scope.fn_PITTradFilter($scope.scripcode, $scope.FromDates, $scope.ToDates);



    }



    $rootScope.$on('$includeContentLoaded', function (event, url) {

        //console.log(event);

        //console.log(url);

        if (url == '/GetQuote/stk_PIT_trading_plan.html') {

            $('#collapse4').removeClass("panel-collapse collapse");

            $('#collapse4').addClass("panel-collapse collapse in");

            $('#l123').removeClass("panel panel-active");

            $('#l123').addClass("list-group-item");

            var cls = $('#collapse4').attr('class');

            if (cls == 'panel-collapse collapse in') {

                $('#l123').removeClass("list-group-item");

                $('#l123').addClass("panel panel-active");

                $('#l123').parent().addClass("divpanel-ative");

                $('#collapse4').css('display', 'block');

            }

        }

    });
}]);

//Function for SDD Shareholding //new development

getquote.constant('serviceurl134', {
    url_Sharehldindex: 'shpsddsecurity_index/w',
    url_SddSharehld_Decelaration: 'shpsddsecurity_declaration/w',
    url_sddshpsummary: 'shpsddsecurity_summarypar/w'
});

getquote.controller('sddshpController', ['serviceurl134', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function sddshpController(serviceurl134, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {

    $scope.loader = {
        SHSecState: 'loading',
        SHSecdelay: false,
    };

    var querystr = $location.absUrl().replace(/[\\#,+()$~%":*<>{};]/g, '_');
    var qtrid = "";
    var scripcode;
    var benposedate = "";
    var type;
    var totalItems = 0;
    $scope.getUrlParameter = function (param, dummyPath) {
        var sPageURL = dummyPath || window.location.search.substring(1),
            sURLVariables = sPageURL.split(/[&||?]/),
            res;
        for (var i = 0; i < sURLVariables.length; i += 1) {
            var paramName = sURLVariables[i],
                sParameterName = (paramName || '').split('=');
            if (sParameterName[0] === param) {
                res = sParameterName[1];
            }
        }
        return res;
    }
    if (querystr.indexOf('=') == -1) {
        var a = querystr.split('/')
        scripcode = a[6];
        type = a[5];
        if (a.length > 7 && a[7] == "qtrid") {
            $scope.qtrid = a[10];
        }
    }
    else {
        scripcode = $scope.getUrlParameter('scripcode', querystr);
        $scope.qtrid = $scope.getUrlParameter('qtrid', querystr);
    }
    //$scope.qtrid = benposedate;
    $rootScope.scripcode = scripcode;

    $scope.fn_Shrhld_SecFlag = function () {
        $scope.loader.SHSecState = 'loading';
        $scope.loader.SHSecdelay = false;
        var url = mainapi.api_domainLIVE + serviceurl134.url_Sharehld_flag;
        $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode, qtrid: $scope.qtrid } }).then(function (response) {
            $scope.ShrhldFlag = response.data;
            $scope.loader.SHSecState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHSecdelay = true;
                $scope.loader.SHSecState = 'loading';
            }
        });
    }

    $scope.fn_Shrhld_index = function () {
        $scope.loader.SHSecState = 'loading';
        $scope.loader.SHSecdelay = false;
        var url = mainapi.newapi_domain + serviceurl134.url_Sharehldindex;
        var urlF = $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode, benposedate: $scope.qtrid } }).then(function (response) {

            $scope.SDDShrhldSummary = response.data;
            $scope.loader.SHSecState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHSecdelay = true;
                $scope.loader.SHSecState = 'loading';
                $scope.Norecordfound = "No Record Found";
            }
        });
    }
    $scope.fn_sddShpDeclaration = function () {
        $scope.loader.SHSecState = 'loading';
        $scope.loader.SHSecdelay = false;
        var url = mainapi.newapi_domain + serviceurl134.url_SddSharehld_Decelaration;
        var urlF = $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode, benposedate: $scope.qtrid } }).then(function (response) {
            $scope.SDDShrhldDeclaration = response.data;
            $scope.loader.SHSecState = 'loaded';
            //$scope.fn_shareholdingTitle($scope.ShrhldDeclaration[0].qtr_name);
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHSecdelay = true;
                $scope.loader.SHSecState = 'loading';

            }
        });
    }


    $scope.fn_Shrhld_summary = function () {
        $scope.loader.SHSecState = 'loading';
        $scope.loader.SHSecdelay = false;
        var url = mainapi.newapi_domain + serviceurl134.url_sddshpsummary;
        var urlF = $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode, benposedate: $scope.qtrid } }).then(function (response) {

            $scope.SDDShrhldSummarydata = response.data;
            $scope.loader.SHSecState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHSecdelay = true;
                $scope.loader.SHSecState = 'loading';
                $scope.Norecordfound = "No Record Found";
            }
        });
    }

    $scope.trustAsHtmllshp = function (string) {
        return $sce.trustAsHtml(string);
    };


    $scope.checkdebtscrip = function () {
        var deb = "/stock-share-price/debt-other/scripcode/" + $scope.scripcode + "/";
        if ($scope.scripcode >= 700000 && $scope.scripcode <= 999999) {
            return true;
        }
        else {
            return false;
        }

    };
}]);
//for Integrated filing
getquote.constant('serviceurl35', {
    url_integratedfiling: 'Integratedfiledata/w',
    url_integratedfilingfinance: 'Integratedfinancedata/w'
});

getquote.controller('IntegratefileGovernanceController', ['serviceurl35', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function IntegratefileGovernanceController(serviceurl35, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {



    $scope.loader = {
        REState: 'loading',
        REdelay: false,
    };

    var querystr = $location.absUrl().replace(/[\\#,+()$~%":*<>{};]/g, '_');
    var scripcode;
    var benposedate = "";
    $scope.getUrlParameter = function (param, dummyPath) {
        var sPageURL = dummyPath || window.location.search.substring(1),
            sURLVariables = sPageURL.split(/[&||?]/),
            res;
        for (var i = 0; i < sURLVariables.length; i += 1) {
            var paramName = sURLVariables[i],
                sParameterName = (paramName || '').split('=');
            if (sParameterName[0] === param) {
                res = sParameterName[1];
            }
        }
        return res;
    }
    if (querystr.indexOf('=') == -1) {
        var a = querystr.split('/')
        scripcode = a[6];
        type = a[5];
        if (a.length > 7 && a[7] == "qtrid") {
            qtrid = a[8];
        }
    }
    else {
        scripcode = $scope.getUrlParameter('scripcode', querystr);
        qtrid = $scope.getUrlParameter('qtrid', querystr);
    }
    $rootScope.scripcode = scripcode;


    $scope.fn_integratedfiling = function () {
        $scope.loader.SHState = 'loading';
        $scope.loader.SHdelay = false;
        var url = mainapi.newapi_domain + serviceurl35.url_integratedfiling;
        var urlF = $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode } }).then(function (response) {

            $scope.integratedfiledata = response.data;
            $scope.loader.SHState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHdelay = true;
                $scope.loader.SHState = 'loading';
            }
        });
    };
    $scope.fn_integratedfilingfinance = function () {
        $scope.loader.SHState = 'loading';
        $scope.loader.SHdelay = false;
        var url = mainapi.newapi_domain + serviceurl35.url_integratedfilingfinance;
        var urlF = $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode } }).then(function (response) {

            $scope.integratedfilefinancedata = response.data;
            $scope.loader.SHState = 'loaded';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.SHdelay = true;
                $scope.loader.SHState = 'loading';
            }
        });
    };

    $scope.trustAsHtml = function (string) {
        return $sce.trustAsHtml(string);
    };



}]);

//For Disclosures CRA
getquote.constant('serviceurl135', {
    url_Creditrating: "CreDisclosureditRatingData/w",
    url_DwnldExcelCRA: "DownloadDisclosurecreditratingcsv/w"
})

getquote.controller('disintermeCRA_controller', ['serviceurl135', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function disintermeCRA_controller(serviceurl135, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {





    $scope.loader = {

        CRAState: 'loading',
        CRAdelay: false,
    };
    var querystr = $location.absUrl().replace(/[\\#,+()$~%":*<>{};]/g, '_');
    var scripcode;
    var benposedate = "";
    $scope.getUrlParameter = function (param, dummyPath) {
        var sPageURL = dummyPath || window.location.search.substring(1),
            sURLVariables = sPageURL.split(/[&||?]/),
            res;
        for (var i = 0; i < sURLVariables.length; i += 1) {
            var paramName = sURLVariables[i],
                sParameterName = (paramName || '').split('=');
            if (sParameterName[0] === param) {
                res = sParameterName[1];
            }
        }
        return res;
    }
    if (querystr.indexOf('=') == -1) {
        var a = querystr.split('/')
        scripcode = a[6];
        type = a[5];

    }
    else {
        scripcode = $scope.getUrlParameter('scripcode', querystr);

    }
    $rootScope.scripcode = scripcode;
    /* $rootScope.scripcode = "";*/

    $scope.FromDate = '';//null;
    $scope.ToDate = '';//null;

    $scope.viewby = 30;
    $scope.pageSize = 10;
    $scope.totalItems = 0;
    $scope.currentPage = 1;
    $scope.pagenumber = 0;
    $scope.loader.prevDisp = true;
    $scope.loader.NextDisp = true;
    $scope.itemsPerPage = $scope.viewby;
    $scope.maxSize = 5; //Number of pager buttons to show
    $scope.Submission = 'Select';
    $("#ddlresubmission :selected").text() == "Select"
    $scope.fn_PrevcraPage = function () {

        if ($scope.currentPage == 1) {
            $('#idprev').hide();
        }
        else if ($scope.currentPage != 1) {
            $scope.currentPage = $scope.currentPage - 1;
            $scope.fn_Disclosurecra($scope.currentPage);
        }
    }
    $scope.fn_NextcraPage = function () {
        if ($scope.currentPage < $scope.pagenumber) {
            $scope.currentPage = $scope.currentPage + 1;
            $scope.fn_Disclosurecra($scope.currentPage);
        }

        if ($scope.currentPage == $scope.pagenumber) {
            $('#idnext').hide();
            $scope.loader.NextDisp = false;
        }
    }

    $scope.fn_Disclosurecra = function (Pagenoa) {
        //debugger;
        $scope.loader.CRAState = 'loading';
        $scope.loader.CRAdelay = false;
        $scope.currentPage1 = Pagenoa;
        if ($scope.Isin == undefined || $scope.Isin == null)
            $scope.Isin = "";
        if ($scope.dueFromDate == undefined || $scope.dueFromDate == null)
            $scope.dueFromDate = "";
        if ($scope.dueToDate == undefined || $scope.dueToDate == null)
            $scope.dueToDate = "";
        if ($scope.Submission == undefined || $scope.Submission == null)
            $scope.Submission = "";
        if ($scope.TimeToDate == undefined || $scope.TimeToDate == null)
            $scope.TimeToDate = "";
        if ($scope.TimeFromDate == undefined || $scope.TimeFromDate == null)
            $scope.TimeFromDate = "";
        if ($scope.Submission == undefined || $scope.Submission == null || $scope.Submission == "Select")
            $scope.Submission = "";
        //if ($("#ddlresubmission :selected").text() == "Select") {
        //    $scope.Submission = "";
        //}
        //else {
        //    $scope.Submission = $('#ddlresubmission option:selected').val();
        //}
        var url = mainapi.api_domainLIVE + serviceurl135.url_Creditrating;
        $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode, ISIN: $scope.Isin, duefromdt: $scope.dueFromDate, duetodt: $scope.dueToDate, Resubmission: $scope.Submission, Timesubfromdt: $scope.TimeFromDate, Timesubtodt: $scope.TimeToDate } }).then(function successCallback(response) {
            $scope.Disclosurecra = response.data;
            $scope.loader.CRAState = 'loaded';
            $scope.totalItems = $scope.Disclosurecra.Table.length;
            $scope.Submission = "Select";
            if ($scope.totalItems <= 30) {
                $scope.pagenumber = 1;
                $scope.loader.NextDisp = false;
                $scope.loader.prevDisp = false;
            }
            else {
                $scope.pagenumber = Math.ceil($scope.totalItems / 30);

                //if ($scope.currentPage >= $scope.pagenumber && $scope.pagenumber!=1) { 

                if ($scope.currentPage == $scope.pagenumber) { $scope.loader.NextDisp = false }

                else if ($scope.currentPage < $scope.pagenumber) { $scope.loader.NextDisp = true; }
                else {
                    $scope.loader.NextDisp = true;
                    $scope.loader.prevDisp = true;
                }
            }
            //$scope.apply_pagination();
            //$scope.TotalRecs = $scope.InsiderTrade.Table.length;
            //var x = document.getElementsByTagName("PAGING");
            //x[0].attributes[2].value = '"' + $scope.TotalRecs + '"';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.CRAdelay = true;
                $scope.loader.CRAState = 'loading';
            }
        });

    }

    $scope.fn_Disclosurecrafilter = function (Isin, duefromdate, duetodate, timefromdate, timetodate, Submission) {
        $scope.loader.CRAState = 'loading';
        $scope.loader.CRAdelay = false;
        $scope.currentPage = 1;
        $scope.pagenumber = 0;

        var url = mainapi.api_domainLIVE + serviceurl135.url_Creditrating;
        $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode, ISIN: Isin, duefromdt: duefromdate, duetodt: duetodate, Resubmission: Submission, Timesubfromdt: timefromdate, Timesubtodt: timetodate } }).then(function successCallback(response) {
            $scope.Disclosurecra = response.data;
            $scope.loader.CRAState = 'loaded';
            $scope.totalItems = $scope.Disclosurecra.Table.length;
            if ($scope.Submission == "")
                $scope.Submission = "Select";
            if ($scope.totalItems <= 30) {
                $scope.pagenumber = 1;
                $scope.loader.NextDisp = false;
                $scope.loader.prevDisp = false;
            }
            else {
                $scope.pagenumber = Math.ceil($scope.totalItems / 30);

                //if ($scope.currentPage >= $scope.pagenumber && $scope.pagenumber!=1) { 

                if ($scope.currentPage == $scope.pagenumber) { $scope.loader.NextDisp = false }

                else if ($scope.currentPage < $scope.pagenumber) { $scope.loader.NextDisp = true; }
                else {
                    $scope.loader.NextDisp = true;
                    $scope.loader.prevDisp = true;
                }
            }

        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.CRAdelay = true;
                $scope.loader.CRAState = 'loading';
            }
        });

    }

    $scope.fn_disclosurecrasubmit = function () {
        debugger;
        $scope.valid = false;
        var duefromdate;
        var duetodate;
        var timefromdate;
        var timetodate;

        //if ($("#ddlresubmission :selected").text() == "Select") {
        //    $scope.Submission = "";
        //}
        //else {
        //    $scope.Submission = $('#ddlresubmission option:selected').val();
        //}
        if ($scope.Isin == undefined || $scope.Isin == null || $scope.Isin == "")
            $scope.Isin = "";
        if ($scope.dueFromDate == undefined || $scope.dueFromDate == null || $scope.dueFromDate == "")
            duefromdate = "";
        else
            duefromdate = $scope.dueFromDate;
        if ($scope.dueToDate == undefined || $scope.dueToDate == null || $scope.dueToDate == "")
            duetodate = "";
        else
            duetodate = $scope.dueToDate;
        if ($scope.Submission == undefined || $scope.Submission == null || $scope.Submission == "Select")
            $scope.Submission = "";
        else {
            $scope.Submission = $('#ddlresubmission option:selected').val();
        }
        if ($scope.TimeFromDate == undefined || $scope.TimeFromDate == null || $scope.TimeFromDate == "")
            timefromdate = "";
        else
            timefromdate = $scope.TimeFromDate;
        if ($scope.TimeToDate == undefined || $scope.TimeToDate == null || $scope.TimeToDate == "")
            timetodate = "";
        else
            timetodate = $scope.TimeToDate;
        if (duefromdate != "" && duetodate != "") {
            var fmdt = new Date($scope.dueFromDate.split('/')[2], $scope.dueFromDate.split('/')[1] - 1, $scope.dueFromDate.split('/')[0]);
            var todt = new Date($scope.dueToDate.split('/')[2], $scope.dueToDate.split('/')[1] - 1, $scope.dueToDate.split('/')[0]);
            const oneDay = 24 * 60 * 60 * 1000; // hours*minutes*seconds*milliseconds
            const firstDate = new Date(fmdt);
            const secondDate = new Date(todt);
            const diffDays = Math.round(Math.abs((firstDate - secondDate) / oneDay));
            if (fmdt > todt) {
                $scope.valid = false;
                alert('From date should be less than To date'); return false;
            }
            //else if (diffDays > 92) {
            //    alert('Period should not be more than 3 month'); return false;
            //}
            else {
                $scope.valid = true;
                duefromdate = $scope.dueFromDate.split('/')[2] + "-" + $scope.dueFromDate.split('/')[1] + "-" + $scope.dueFromDate.split('/')[0];
                duetodate = $scope.dueToDate.split('/')[2] + "-" + $scope.dueToDate.split('/')[1] + "-" + $scope.dueToDate.split('/')[0];
                //$scope.fn_InsiderTrd15filter($scope.FromDate, $scope.ToDate);
            }
        }
        else if (duetodate != "" && duefromdate == "") {
            $scope.valid = false;
            alert('Please enter From Date');
        }
        else if (duetodate == "" && duefromdate != "") {
            $scope.valid = false;
            alert('Please enter To Date');
        }
        if (duefromdate == "" && duetodate == "") {
            $scope.valid = true;
        }
        if (timefromdate == "" && timetodate == "") {
            $scope.valid = true;
        }
        if (timefromdate != "" && timetodate != "") {
            var fmdt = new Date($scope.TimeFromDate.split('/')[2], $scope.TimeFromDate.split('/')[1] - 1, $scope.TimeFromDate.split('/')[0]);
            var todt = new Date($scope.TimeToDate.split('/')[2], $scope.TimeToDate.split('/')[1] - 1, $scope.TimeToDate.split('/')[0]);
            const oneDay = 24 * 60 * 60 * 1000; // hours*minutes*seconds*milliseconds
            const firstDate = new Date(fmdt);
            const secondDate = new Date(todt);
            const diffDays = Math.round(Math.abs((firstDate - secondDate) / oneDay));
            if (fmdt > todt) {
                $scope.valid = false;
                alert('From date should be less than To date'); return false;
            }
            //else if (diffDays > 92) {
            //    alert('Period should not be more than 3 month'); return false;
            //}
            else {
                $scope.valid = true;
                var timefromdate = $scope.TimeFromDate.split('/')[2] + "-" + $scope.TimeFromDate.split('/')[1] + "-" + $scope.TimeFromDate.split('/')[0];
                var timetodate = $scope.TimeToDate.split('/')[2] + "-" + $scope.TimeToDate.split('/')[1] + "-" + $scope.TimeToDate.split('/')[0];
                //$scope.fn_InsiderTrd15filter($scope.FromDate, $scope.ToDate);
            }
        }
        else if (timetodate != "" && timefromdate == "") {
            $scope.valid = false;
            alert('Please enter From Date');
        }
        else if (timetodate == "" && timefromdate != "") {
            $scope.valid = false;
            alert('Please enter To Date');
        }
        if ($scope.valid == true) {
            $scope.fn_Disclosurecrafilter($scope.Isin, duefromdate, duetodate, timefromdate, timetodate, $scope.Submission);
        }
    }


    $scope.fn_downloadexcelcra = function () {
        $scope.valid = false;
        var duefromdate;
        var duetodate;
        var timefromdate;
        var timetodate;
        if ($scope.Isin == undefined || $scope.Isin == null || $scope.Isin == "")
            $scope.Isin = "";
        if ($scope.dueFromDate == undefined || $scope.dueFromDate == null || $scope.dueFromDate == "")
            duefromdate = "";
        if ($scope.dueToDate == undefined || $scope.dueToDate == null || $scope.dueToDate == "")
            duetodate = "";
        if ($scope.Submission == undefined || $scope.Submission == null || $scope.Submission == "Select")
            $scope.Submission = "";
        else {
            $scope.Submission = $('#ddlresubmission option:selected').val();
        }
        if ($scope.TimeFromDate == undefined || $scope.TimeFromDate == null || $scope.TimeFromDate == "")
            timefromdate = "";
        if ($scope.TimeToDate == undefined || $scope.TimeToDate == null || $scope.TimeToDate == "")
            timetodate = "";
        if (duefromdate != "" && duetodate != "") {
            duefromdate = $scope.dueFromDate.split('/')[2] + "-" + $scope.dueFromDate.split('/')[1] + "-" + $scope.dueFromDate.split('/')[0];
            duetodate = $scope.dueToDate.split('/')[2] + "-" + $scope.dueToDate.split('/')[1] + "-" + $scope.dueToDate.split('/')[0];

        }

        if (timefromdate != "" && timetodate != "") {

            var timefromdate = $scope.TimeFromDate.split('/')[2] + "-" + $scope.TimeFromDate.split('/')[1] + "-" + $scope.TimeFromDate.split('/')[0];
            var timetodate = $scope.TimeToDate.split('/')[2] + "-" + $scope.TimeToDate.split('/')[1] + "-" + $scope.TimeToDate.split('/')[0];

        }


        var url = mainapi.api_domainLIVE + serviceurl135.url_DwnldExcelCRA + "?scripcode=" + $rootScope.scripcode + "&ISIN=" + $scope.Isin + "&duefromdt=" + duefromdate + "&duetodt=" + duetodate + "&Resubmission=" + $scope.Submission + "&Timesubfromdt=" + timefromdate + "&Timesubtodt=" + timetodate;
        if ($scope.Submission == "")
            $scope.Submission = "Select";

        window.open(url, "_self");


    }



    $rootScope.$on('$includeContentLoaded', function (event, url) {
        //console.log(event);
        // console.log(url);
        if (url == '/GetQuote/stk_intermecra.html') {
            $('#collapse4').removeClass("panel-collapse collapse");
            $('#collapse4').addClass("panel-collapse collapse in");
            $('#l121').removeClass("panel panel-active");
            $('#l121').addClass("list-group-item");
            var cls = $('#collapse4').attr('class');
            if (cls == 'panel-collapse collapse in') {
                $('#l121').removeClass("list-group-item");
                $('#l121').addClass("panel panel-active");
                $('#l121').parent().addClass("divpanel-ative");
                $('#collapse4').css('display', 'block');
            }
        }
    });

    $scope.recallFunction = function () {
        $timeout(function () {
            if ($scope.loader.delay == true) { $scope.fn_Disclosurecra($scope.currentPage); }
            $scope.recallFunction();
        }, 20000)
    };
    $scope.recallFunction();


}]);
//Rating Action
getquote.constant('serviceurl137', {
    url_RatingAction: "DiscRatingAction/w",
    url_DwnldExcelRA: "DownloadDiscRatingActioncsv/w",
    url_racreditdropdown: "RACreditratingDropdown/w"
})

getquote.controller('disinterRatingaction_controller', ['serviceurl137', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function disinterRatingaction_controller(serviceurl137, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {





    $scope.loader = {

        CRAState: 'loading',
        CRAdelay: false,
    };
    var querystr = $location.absUrl().replace(/[\\#,+()$~%":*<>{};]/g, '_');
    var scripcode;
    var benposedate = "";
    $scope.getUrlParameter = function (param, dummyPath) {
        var sPageURL = dummyPath || window.location.search.substring(1),
            sURLVariables = sPageURL.split(/[&||?]/),
            res;
        for (var i = 0; i < sURLVariables.length; i += 1) {
            var paramName = sURLVariables[i],
                sParameterName = (paramName || '').split('=');
            if (sParameterName[0] === param) {
                res = sParameterName[1];
            }
        }
        return res;
    }
    if (querystr.indexOf('=') == -1) {
        var a = querystr.split('/')
        scripcode = a[6];
        type = a[5];

    }
    else {
        scripcode = $scope.getUrlParameter('scripcode', querystr);

    }
    $rootScope.scripcode = scripcode;
    /* $rootScope.scripcode = "";*/

    $scope.FromDate = '';//null;
    $scope.ToDate = '';//null;

    $scope.viewby = 30;
    $scope.pageSize = 10;
    $scope.totalItems = 0;
    $scope.currentPage = 1;
    $scope.pagenumber = 0;
    $scope.loader.prevDisp = true;
    $scope.loader.NextDisp = true;
    $scope.itemsPerPage = $scope.viewby;
    $scope.maxSize = 5; //Number of pager buttons to show
    $scope.creditrating = 'Select';
    $("#ddlcreditrating :selected").text() == "Select"
    $scope.fn_PrevRAPage = function () {

        if ($scope.currentPage == 1) {
            $('#idprev').hide();
        }
        else if ($scope.currentPage != 1) {
            $scope.currentPage = $scope.currentPage - 1;
            $scope.fn_DisclosureRA($scope.currentPage);
        }
    }
    $scope.fn_NextRAPage = function () {
        if ($scope.currentPage < $scope.pagenumber) {
            $scope.currentPage = $scope.currentPage + 1;
            $scope.fn_DisclosureRA($scope.currentPage);
        }

        if ($scope.currentPage == $scope.pagenumber) {
            $('#idnext').hide();
            $scope.loader.NextDisp = false;
        }
    }
    $scope.fn_Creditratingdropdown = function () {
        //debugger;
        $scope.loader.CRAState = 'loading';
        $scope.loader.CRAdelay = false;
      
        var url = mainapi.api_domainLIVE + serviceurl137.url_racreditdropdown;
        $http({ url: url, method: "GET", params: { } }).then(function successCallback(response) {
            $scope.CRDropdown = response.data;
            $scope.loader.CRAState = 'loaded';
           
            
          
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.CRAdelay = true;
                $scope.loader.CRAState = 'loading';
            }
        });

    }
    $scope.fn_DisclosureRA = function (Pagenoa) {
        //debugger;
        $scope.loader.CRAState = 'loading';
        $scope.loader.CRAdelay = false;
        $scope.currentPage1 = Pagenoa;
        if ($scope.Isin == undefined || $scope.Isin == null)
            $scope.Isin = "";
     
        if ($scope.Submission == undefined || $scope.Submission == null)
            $scope.Submission = "";
        if ($scope.TimeToDate == undefined || $scope.TimeToDate == null)
            $scope.TimeToDate = "";
        if ($scope.TimeFromDate == undefined || $scope.TimeFromDate == null)
            $scope.TimeFromDate = "";
        if ($scope.creditrating == undefined || $scope.creditrating == null || $scope.creditrating == "Select")
            $scope.creditrating = "";
       
        var url = mainapi.api_domainLIVE + serviceurl137.url_RatingAction;
        $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode, ISIN: $scope.Isin, creditrating: $scope.creditrating, Timesubfromdt: $scope.TimeFromDate, Timesubtodt: $scope.TimeToDate } }).then(function successCallback(response) {
            $scope.DisclosureRA = response.data;
            $scope.loader.CRAState = 'loaded';
            $scope.totalItems = $scope.DisclosureRA.Table.length;
            $scope.creditrating = "Select";
            if ($scope.totalItems <= 30) {
                $scope.pagenumber = 1;
                $scope.loader.NextDisp = false;
                $scope.loader.prevDisp = false;
            }
            else {
                $scope.pagenumber = Math.ceil($scope.totalItems / 30);

                //if ($scope.currentPage >= $scope.pagenumber && $scope.pagenumber!=1) { 

                if ($scope.currentPage == $scope.pagenumber) { $scope.loader.NextDisp = false }

                else if ($scope.currentPage < $scope.pagenumber) { $scope.loader.NextDisp = true; }
                else {
                    $scope.loader.NextDisp = true;
                    $scope.loader.prevDisp = true;
                }
            }
            //$scope.apply_pagination();
            //$scope.TotalRecs = $scope.InsiderTrade.Table.length;
            //var x = document.getElementsByTagName("PAGING");
            //x[0].attributes[2].value = '"' + $scope.TotalRecs + '"';
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.CRAdelay = true;
                $scope.loader.CRAState = 'loading';
            }
        });

    }

    $scope.fn_DisclosureRAfilter = function (Isin, timefromdate, timetodate, creditrating) {
        $scope.loader.CRAState = 'loading';
        $scope.loader.CRAdelay = false;
        $scope.currentPage = 1;
        $scope.pagenumber = 0;

        var url = mainapi.api_domainLIVE + serviceurl137.url_RatingAction;
        $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode, ISIN: Isin, creditrating: creditrating, Timesubfromdt: timefromdate, Timesubtodt: timetodate } }).then(function successCallback(response) {
            $scope.DisclosureRA = response.data;
            $scope.loader.CRAState = 'loaded';
            $scope.totalItems = $scope.DisclosureRA.Table.length;
            if ($scope.creditrating == "")
                $scope.creditrating = "Select";
            if ($scope.totalItems <= 30) {
                $scope.pagenumber = 1;
                $scope.loader.NextDisp = false;
                $scope.loader.prevDisp = false;
            }
            else {
                $scope.pagenumber = Math.ceil($scope.totalItems / 30);

                //if ($scope.currentPage >= $scope.pagenumber && $scope.pagenumber!=1) { 

                if ($scope.currentPage == $scope.pagenumber) { $scope.loader.NextDisp = false }

                else if ($scope.currentPage < $scope.pagenumber) { $scope.loader.NextDisp = true; }
                else {
                    $scope.loader.NextDisp = true;
                    $scope.loader.prevDisp = true;
                }
            }

        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.CRAdelay = true;
                $scope.loader.CRAState = 'loading';
            }
        });

    }

    $scope.fn_disclosureRAsubmit = function () {
        debugger;
        $scope.valid = false;
        var duefromdate;
        var duetodate;
        var timefromdate;
        var timetodate;

      
        if ($scope.Isin == undefined || $scope.Isin == null || $scope.Isin == "")
            $scope.Isin = "";
       
        if ($scope.creditrating == undefined || $scope.creditrating == null || $scope.creditrating == "Select")
            $scope.creditrating = "";
        else {
            $scope.creditrating = $('#ddlcreditrating option:selected').val();
        }
        if ($scope.TimeFromDate == undefined || $scope.TimeFromDate == null || $scope.TimeFromDate == "")
            timefromdate = "";
        else
            timefromdate = $scope.TimeFromDate;
        if ($scope.TimeToDate == undefined || $scope.TimeToDate == null || $scope.TimeToDate == "")
            timetodate = "";
        else
            timetodate = $scope.TimeToDate;
        
        if (timefromdate == "" && timetodate == "") {
            $scope.valid = true;
        }
        if (timefromdate != "" && timetodate != "") {
            var fmdt = new Date($scope.TimeFromDate.split('/')[2], $scope.TimeFromDate.split('/')[1] - 1, $scope.TimeFromDate.split('/')[0]);
            var todt = new Date($scope.TimeToDate.split('/')[2], $scope.TimeToDate.split('/')[1] - 1, $scope.TimeToDate.split('/')[0]);
            const oneDay = 24 * 60 * 60 * 1000; // hours*minutes*seconds*milliseconds
            const firstDate = new Date(fmdt);
            const secondDate = new Date(todt);
            const diffDays = Math.round(Math.abs((firstDate - secondDate) / oneDay));
            if (fmdt > todt) {
                $scope.valid = false;
                alert('From date should be less than To date'); return false;
            }
            //else if (diffDays > 92) {
            //    alert('Period should not be more than 3 month'); return false;
            //}
            else {
                $scope.valid = true;
                var timefromdate = $scope.TimeFromDate.split('/')[2] + "-" + $scope.TimeFromDate.split('/')[1] + "-" + $scope.TimeFromDate.split('/')[0];
                var timetodate = $scope.TimeToDate.split('/')[2] + "-" + $scope.TimeToDate.split('/')[1] + "-" + $scope.TimeToDate.split('/')[0];
                //$scope.fn_InsiderTrd15filter($scope.FromDate, $scope.ToDate);
            }
        }
        else if (timetodate != "" && timefromdate == "") {
            $scope.valid = false;
            alert('Please enter From Date');
        }
        else if (timetodate == "" && timefromdate != "") {
            $scope.valid = false;
            alert('Please enter To Date');
        }
        if ($scope.valid == true) {
            $scope.fn_DisclosureRAfilter($scope.Isin, timefromdate, timetodate, $scope.creditrating);
        }
    }


    $scope.fn_downloadexcelRA = function () {
        $scope.valid = false;
        var duefromdate;
        var duetodate;
        var timefromdate;
        var timetodate;
        if ($scope.Isin == undefined || $scope.Isin == null || $scope.Isin == "")
            $scope.Isin = "";
        //if ($scope.dueFromDate == undefined || $scope.dueFromDate == null || $scope.dueFromDate == "")
        //    duefromdate = "";
        //if ($scope.dueToDate == undefined || $scope.dueToDate == null || $scope.dueToDate == "")
        //    duetodate = "";
        if ($scope.creditrating == undefined || $scope.creditrating == null || $scope.creditrating == "Select")
            $scope.creditrating = "";
        else {
            $scope.creditrating = $('#ddlcreditrating option:selected').val();
        }
        if ($scope.TimeFromDate == undefined || $scope.TimeFromDate == null || $scope.TimeFromDate == "")
            timefromdate = "";
        if ($scope.TimeToDate == undefined || $scope.TimeToDate == null || $scope.TimeToDate == "")
            timetodate = "";
        //if (duefromdate != "" && duetodate != "") {
        //    duefromdate = $scope.dueFromDate.split('/')[2] + "-" + $scope.dueFromDate.split('/')[1] + "-" + $scope.dueFromDate.split('/')[0];
        //    duetodate = $scope.dueToDate.split('/')[2] + "-" + $scope.dueToDate.split('/')[1] + "-" + $scope.dueToDate.split('/')[0];

        //}

        if (timefromdate != "" && timetodate != "") {

            var timefromdate = $scope.TimeFromDate.split('/')[2] + "-" + $scope.TimeFromDate.split('/')[1] + "-" + $scope.TimeFromDate.split('/')[0];
            var timetodate = $scope.TimeToDate.split('/')[2] + "-" + $scope.TimeToDate.split('/')[1] + "-" + $scope.TimeToDate.split('/')[0];

        }


        var url = mainapi.api_domainLIVE + serviceurl137.url_DwnldExcelRA + "?scripcode=" + $rootScope.scripcode + "&ISIN=" + $scope.Isin + "&creditrating=" + $scope.creditrating + "&Timesubfromdt=" + timefromdate + "&Timesubtodt=" + timetodate;
        if ($scope.creditrating == "")
            $scope.creditrating = "Select";

        window.open(url, "_self");


    }



    $rootScope.$on('$includeContentLoaded', function (event, url) {
        //console.log(event);
        // console.log(url);
        if (url == '/GetQuote/stk_intermRatingAction.html') {
            $('#collapse4').removeClass("panel-collapse collapse");
            $('#collapse4').addClass("panel-collapse collapse in");
            $('#l121').removeClass("panel panel-active");
            $('#l121').addClass("list-group-item");
            var cls = $('#collapse4').attr('class');
            if (cls == 'panel-collapse collapse in') {
                $('#l121').removeClass("list-group-item");
                $('#l121').addClass("panel panel-active");
                $('#l121').parent().addClass("divpanel-ative");
                $('#collapse4').css('display', 'block');
            }
        }
    });

    $scope.recallFunction = function () {
        $timeout(function () {
            if ($scope.loader.delay == true) { $scope.fn_DisclosureRA($scope.currentPage); }
            $scope.recallFunction();
        }, 20000)
    };
    $scope.recallFunction();


}]);
//New ERP added -- shweta mhatre
getquote.constant('serviceurl36', {
    url_erpdetails: 'intermediscERP/w',
    url_erpdetailsdownload: 'DownloadERPcsv/w'
    
});

//ERP Controller 
getquote.controller('erpController', ['serviceurl36', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function erpController(serviceurl36, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {



    $scope.loader = {

        ERPState: 'loading',
        ERPdelay: false,
    };
    var querystr = $location.absUrl().replace(/[\\#,+()$~%":*<>{};]/g, '_');
    var scripcode;
    var benposedate = "";
    $scope.getUrlParameter = function (param, dummyPath) {
        var sPageURL = dummyPath || window.location.search.substring(1),
            sURLVariables = sPageURL.split(/[&||?]/),
            res;
        for (var i = 0; i < sURLVariables.length; i += 1) {
            var paramName = sURLVariables[i],
                sParameterName = (paramName || '').split('=');
            if (sParameterName[0] === param) {
                res = sParameterName[1];
            }
        }
        return res;
    }
    if (querystr.indexOf('=') == -1) {
        var a = querystr.split('/')
        scripcode = a[6];
        type = a[5];

    }
    else {
        scripcode = $scope.getUrlParameter('scripcode', querystr);

    }
    $rootScope.scripcode = scripcode;
    /* $rootScope.scripcode = "";*/

    $scope.FromDate = '';//null;
    $scope.ToDate = '';//null;

    $scope.viewby = 30;
    $scope.pageSize = 10;
    $scope.totalItems = 0;
    $scope.currentPage = 1;
    $scope.pagenumber = 0;
    $scope.loader.prevDisp = true;
    $scope.loader.NextDisp = true;
    $scope.itemsPerPage = $scope.viewby;
    $scope.maxSize = 5; //Number of pager buttons to show
    $scope.Submission = 'Select';
    $("#ddlresubmission :selected").text() == "Select"
    $scope.fn_PrevERPPage = function () {

        if ($scope.currentPage == 1) {
            $('#idprev').hide();
        }
        else if ($scope.currentPage != 1) {
            $scope.currentPage = $scope.currentPage - 1;
            $scope.fn_erpdata($scope.currentPage);
        }
    }
    $scope.fn_NextERPPage = function () {
        if ($scope.currentPage < $scope.pagenumber) {
            $scope.currentPage = $scope.currentPage + 1;
            $scope.fn_erpdata($scope.currentPage);
        }

        if ($scope.currentPage == $scope.pagenumber) {
            $('#idnext').hide();
            $scope.loader.NextDisp = false;
        }
    }

    $scope.fn_erpdata = function (Pagenoa) {
        //debugger;
        $scope.loader.ERPState = 'loading';
        $scope.loader.ERPdelay = false;
        $scope.currentPage1 = Pagenoa;
        if ($scope.Isin == undefined || $scope.Isin == null)
            $scope.Isin = "";
       
        if ($scope.Submission == undefined || $scope.Submission == null)
            $scope.Submission = "";
        if ($scope.TimeToDate == undefined || $scope.TimeToDate == null)
            $scope.TimeToDate = "";
        if ($scope.TimeFromDate == undefined || $scope.TimeFromDate == null)
            $scope.TimeFromDate = "";
        if ($scope.Submission == undefined || $scope.Submission == null || $scope.Submission == "Select")
            $scope.Submission = "";
   
        var url = mainapi.api_domainLIVE + serviceurl36.url_erpdetails;
        $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode, ISIN: $scope.Isin, Resubmission: $scope.Submission, Timesubfromdt: $scope.TimeFromDate, Timesubtodt: $scope.TimeToDate } }).then(function successCallback(response) {
            $scope.erpdatadetails = response.data;
            $scope.loader.ERPState = 'loaded';
            $scope.totalItems = $scope.erpdatadetails.Table.length;
            $scope.Submission = "Select";
            if ($scope.totalItems <= 30) {
                $scope.pagenumber = 1;
                $scope.loader.NextDisp = false;
                $scope.loader.prevDisp = false;
            }
            else {
                $scope.pagenumber = Math.ceil($scope.totalItems / 30);

                //if ($scope.currentPage >= $scope.pagenumber && $scope.pagenumber!=1) { 

                if ($scope.currentPage == $scope.pagenumber) { $scope.loader.NextDisp = false }

                else if ($scope.currentPage < $scope.pagenumber) { $scope.loader.NextDisp = true; }
                else {
                    $scope.loader.NextDisp = true;
                    $scope.loader.prevDisp = true;
                }
            }
            
        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.ERPdelay = true;
                $scope.loader.ERPState = 'loading';
            }
        });

    }

    $scope.fn_ERPDatafilter = function (Isin, timefromdate, timetodate, Submission) {
        $scope.loader.ERPState = 'loading';
        $scope.loader.ERPdelay = false;
        $scope.currentPage = 1;
        $scope.pagenumber = 0;

        var url = mainapi.api_domainLIVE + serviceurl36.url_erpdetails;
      //  $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode, ISIN: Isin, duefromdt: duefromdate, duetodt: duetodate, Resubmission: Submission, Timesubfromdt: timefromdate, Timesubtodt: timetodate } }).then(function successCallback(response) {
        $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode, ISIN: Isin, Resubmission: Submission, Timesubfromdt: timefromdate, Timesubtodt: timetodate } }).then(function successCallback(response) {
            $scope.erpdatadetails = response.data;
            $scope.loader.ERPState = 'loaded';
            $scope.totalItems = $scope.erpdatadetails.Table.length;
            if ($scope.Submission == "")
                $scope.Submission = "Select";
            if ($scope.totalItems <= 30) {
                $scope.pagenumber = 1;
                $scope.loader.NextDisp = false;
                $scope.loader.prevDisp = false;
            }
            else {
                $scope.pagenumber = Math.ceil($scope.totalItems / 30);

                //if ($scope.currentPage >= $scope.pagenumber && $scope.pagenumber!=1) { 

                if ($scope.currentPage == $scope.pagenumber) { $scope.loader.NextDisp = false }

                else if ($scope.currentPage < $scope.pagenumber) { $scope.loader.NextDisp = true; }
                else {
                    $scope.loader.NextDisp = true;
                    $scope.loader.prevDisp = true;
                }
            }

        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.ERPdelay = true;
                $scope.loader.ERPState = 'loading';
            }
        });

    }

    $scope.fn_ERPDatasubmit = function () {
       
        $scope.valid = false;
     
        var timefromdate;
        var timetodate;

       
        if ($scope.Isin == undefined || $scope.Isin == null || $scope.Isin == "")
            $scope.Isin = "";
        
        if ($scope.Submission == undefined || $scope.Submission == null || $scope.Submission == "Select")
            $scope.Submission = "";
        else {
            $scope.Submission = $('#ddlresubmission option:selected').val();
        }
        if ($scope.TimeFromDate == undefined || $scope.TimeFromDate == null || $scope.TimeFromDate == "")
            timefromdate = "";
        else
            timefromdate = $scope.TimeFromDate;
        if ($scope.TimeToDate == undefined || $scope.TimeToDate == null || $scope.TimeToDate == "")
            timetodate = "";
        else
            timetodate = $scope.TimeToDate;
       
        if (timefromdate == "" && timetodate == "") {
            $scope.valid = true;
        }
        if (timefromdate != "" && timetodate != "") {
            var fmdt = new Date($scope.TimeFromDate.split('/')[2], $scope.TimeFromDate.split('/')[1] - 1, $scope.TimeFromDate.split('/')[0]);
            var todt = new Date($scope.TimeToDate.split('/')[2], $scope.TimeToDate.split('/')[1] - 1, $scope.TimeToDate.split('/')[0]);
            const oneDay = 24 * 60 * 60 * 1000; // hours*minutes*seconds*milliseconds
            const firstDate = new Date(fmdt);
            const secondDate = new Date(todt);
            const diffDays = Math.round(Math.abs((firstDate - secondDate) / oneDay));
            if (fmdt > todt) {
                $scope.valid = false;
                alert('From date should be less than To date'); return false;
            }
            //else if (diffDays > 92) {
            //    alert('Period should not be more than 3 month'); return false;
            //}
            else {
                $scope.valid = true;
                var timefromdate = $scope.TimeFromDate.split('/')[2] + "-" + $scope.TimeFromDate.split('/')[1] + "-" + $scope.TimeFromDate.split('/')[0];
                var timetodate = $scope.TimeToDate.split('/')[2] + "-" + $scope.TimeToDate.split('/')[1] + "-" + $scope.TimeToDate.split('/')[0];
                //$scope.fn_InsiderTrd15filter($scope.FromDate, $scope.ToDate);
            }
        }
        else if (timetodate != "" && timefromdate == "") {
            $scope.valid = false;
            alert('Please enter From Date');
        }
        else if (timetodate == "" && timefromdate != "") {
            $scope.valid = false;
            alert('Please enter To Date');
        }
        if ($scope.valid == true) {
        //    $scope.fn_ERPDatafilter($scope.Isin, duefromdate, duetodate, timefromdate, timetodate, $scope.Submission);
            $scope.fn_ERPDatafilter($scope.Isin, timefromdate, timetodate, $scope.Submission);
        }
    }

    $scope.fn_downloadexcelerp = function () {
        $scope.valid = false;
        //var duefromdate;
        //var duetodate;
        var timefromdate;
        var timetodate;
        if ($scope.Isin == undefined || $scope.Isin == null || $scope.Isin == "")
            $scope.Isin = "";
       
        if ($scope.Submission == undefined || $scope.Submission == null || $scope.Submission == "Select")
            $scope.Submission = "";
        else {
            $scope.Submission = $('#ddlresubmission option:selected').val();
        }
        if ($scope.TimeFromDate == undefined || $scope.TimeFromDate == null || $scope.TimeFromDate == "")
            timefromdate = "";
        if ($scope.TimeToDate == undefined || $scope.TimeToDate == null || $scope.TimeToDate == "")
            timetodate = "";
       

        if (timefromdate != "" && timetodate != "") {

            var timefromdate = $scope.TimeFromDate.split('/')[2] + "-" + $scope.TimeFromDate.split('/')[1] + "-" + $scope.TimeFromDate.split('/')[0];
            var timetodate = $scope.TimeToDate.split('/')[2] + "-" + $scope.TimeToDate.split('/')[1] + "-" + $scope.TimeToDate.split('/')[0];

        }


        var url = mainapi.api_domainLIVE + serviceurl36.url_erpdetailsdownload + "?scripcode=" + $rootScope.scripcode + "&ISIN=" + $scope.Isin + "&Resubmission=" + $scope.Submission + "&Timesubfromdt=" + timefromdate + "&Timesubtodt=" + timetodate;
        if ($scope.Submission == "")
            $scope.Submission = "Select";

        window.open(url, "_self");


    }
  


    $rootScope.$on('$includeContentLoaded', function (event, url) {
        //console.log(event);
        // console.log(url);
        if (url == '/GetQuote/stk_intermecra.html') {
            $('#collapse4').removeClass("panel-collapse collapse");
            $('#collapse4').addClass("panel-collapse collapse in");
            $('#l121').removeClass("panel panel-active");
            $('#l121').addClass("list-group-item");
            var cls = $('#collapse4').attr('class');
            if (cls == 'panel-collapse collapse in') {
                $('#l121').removeClass("list-group-item");
                $('#l121').addClass("panel panel-active");
                $('#l121').parent().addClass("divpanel-ative");
                $('#collapse4').css('display', 'block');
            }
        }
    });

    $scope.recallFunction = function () {
        $timeout(function () {
            if ($scope.loader.delay == true) { $scope.fn_erpdata($scope.currentPage); }
            $scope.recallFunction();
        }, 20000)
    };
    $scope.recallFunction();
    
}]);



//Function Debt meeting details

getquote.constant('serviceurl43', {
    url_debtmeetingresult: 'DebtMeetinggetdata/w',
 
});
getquote.controller('eqdebtmeetingresultController', ['serviceurl43', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function eqdebtmeetingresultController(serviceurl43, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {
   // debugger;
    $scope.loader = {

       DMState: 'loading',
        DMdelay: false,
    };
    var querystr = $location.absUrl().replace(/[\\#,+()$~%":*<>{};]/g, '_');
    var scripcode;

    $scope.getUrlParameter = function (param, dummyPath) {
        var sPageURL = dummyPath || window.location.search.substring(1),
            sURLVariables = sPageURL.split(/[&||?]/),
            res;
        for (var i = 0; i < sURLVariables.length; i += 1) {
            var paramName = sURLVariables[i],
                sParameterName = (paramName || '').split('=');
            if (sParameterName[0] === param) {
                res = sParameterName[1];
            }
        }
        return res;
    }
    if (querystr.indexOf('=') == -1) {
        var a = querystr.split('/')
        scripcode = a[6];
        type = a[5];

    }
    else {
        scripcode = $scope.getUrlParameter('scripcode', querystr);

    }
    $rootScope.scripcode = scripcode;

    $scope.fn_Debtmeetingata = function () {
        //debugger;
        $scope.loader.DMState = 'loading';
        $scope.loader.DMdelay = false;
       
        var url = mainapi.api_domainLIVE + serviceurl43.url_debtmeetingresult;
        $http({ url: url, method: "GET", params: { sccode: $rootScope.scripcode } }).then(function successCallback(response) {
            $scope.DMData = response.data;
            $scope.loader.DMState = 'loaded';
           

        }, function errorCallback(response) {
            $scope.status = response.status + "_" + response.statusText;
            if (response.status == (500 || 503)) {
                $scope.loader.DMDdelay = true;
                $scope.loader.DMState = 'loading';
            }
        });

    }



   
    $rootScope.$on('$includeContentLoaded', function (event, url) {
        //console.log(event);
        // console.log(url);
        if (url == '/GetQuote/stk_debtmeeting.html') {
            $('#collapse4').removeClass("panel-collapse collapse");
            $('#collapse4').addClass("panel-collapse collapse in");
            $('#l121').removeClass("panel panel-active");
            $('#l121').addClass("list-group-item");
            var cls = $('#collapse4').attr('class');
            if (cls == 'panel-collapse collapse in') {
                $('#l121').removeClass("list-group-item");
                $('#l121').addClass("panel panel-active");
                $('#l121').parent().addClass("divpanel-ative");
                $('#collapse4').css('display', 'block');
            }
        }
    });

    $scope.recallFunction = function () {
        $timeout(function () {
            if ($scope.loader.delay == true) { $scope.fn_Debtmeetingata(); }
            $scope.recallFunction();
        }, 20000)
    };
    $scope.recallFunction();
    $scope.intervalFunction = function () {
        $timeout(function () {
            if (document.visibilityState == "visible") {
                $scope.fn_Debtmeetingata(); 
            }
            $scope.intervalFunction();
        }, 60000);
    };
   
    $scope.intervalFunction();
}]);
//getquote.constant('serviceurl36', {
//    url_erpdetails: 'intermediscERP/w'
//});
//getquote.controller('erpController', ['serviceurl36', '$scope', '$http', '$timeout', '$injector', '$location', '$rootScope', 'mainapi', '$sce', '$window', function erpController(serviceurl36, $scope, $http, $timeout, $injector, $location, $rootScope, mainapi, $sce, $window) {


//    $scope.loader = {
//        CIState: 'loading',
//        CIdelay: false,
//    };

//    var querystr = $location.absUrl().replace(/[\\#,+()$~%.":*<>{};]/g, '_');
//    var flag;
//    var scripcode;
//    var type;
//    var qtrid;
//    $scope.getUrlParameter = function (param, dummyPath) {
//        var sPageURL = dummyPath || window.location.search.substring(1),
//            sURLVariables = sPageURL.split(/[&||?]/),
//            res;
//        for (var i = 0; i < sURLVariables.length; i += 1) {
//            var paramName = sURLVariables[i],
//                sParameterName = (paramName || '').split('=');
//            if (sParameterName[0] === param) {
//                res = sParameterName[1];
//            }
//        }
//        return res;
//    }
//    if (querystr.indexOf('=') == -1) {
//        var a = querystr.split('/')
//        scripcode = a[6];
//        type = a[5];
//        if (a.length > 7 && a[7] == "brsr") {
//        }
//    }
//    else {
//        scripcode = $scope.getUrlParameter('scripcode', querystr);
//        //flag = $scope.getUrlParameter('flag', querystr);
//    }
//    $rootScope.scripcode = scripcode;
//    $scope.selperiod = 0;

//    $scope.checknull = function (entnum) {
//        if (entnum == null || entnum == undefined || entnum == "" || entnum == 0)
//            return true;
//        else
//            return false;
//    }



//    $scope.fn_erpdata = function () {
//        $scope.loader.CIState = 'loading';
//        $scope.loader.CIdelay = false;
//        var url = mainapi.api_domainLIVE + serviceurl36.intermediscERP;
//        var urlF = $http({ url: url, method: "GET", params: { scripcode: $rootScope.scripcode } }).then(function (response) {
//            $scope.erpdatadetails = response.data;
//            $scope.loader.CIState = 'loaded';
//        }, function errorCallback(response) {
//            $scope.status = response.status + "_" + response.statusText;
//            if (response.status == (500 || 503)) {
//                $scope.loader.CIdelay = true;
//                $scope.loader.CIState = 'loading';
//            }
//        });
//    };


//}]);




