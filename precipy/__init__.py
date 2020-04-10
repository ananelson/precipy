PRECIPY_VERSION="0.3.0"

class PrecipyException(Exception):
    pass

class AnalyticsException(PrecipyException):
    pass

class ReportException(PrecipyException):
    pass

class ReportTemplateException(ReportException):
    pass

class ReportFilterException(ReportException):
    pass
