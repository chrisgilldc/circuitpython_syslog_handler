"""
SysLog Handler for Adafruit Logging. Based heavily on the Python core Logging module by Vinay Sajip
and the Syslog handler contributed by Nicolas Untz

Christopher Gill - 2022
"""

import adafruit_esp32spi.adafruit_esp32spi_socket as socket
from adafruit_logging import LoggingHandler
import traceback

SYSLOG_UDP_PORT = 514
SYSLOG_TCP_PORT = 514


class SysLogHandler(LoggingHandler):
    """Syslog handler to send log messages to a syslog server.
    """

    LOG_EMERG     = 0       #  system is unusable
    LOG_ALERT     = 1       #  action must be taken immediately
    LOG_CRIT      = 2       #  critical conditions
    LOG_ERR       = 3       #  error conditions
    LOG_WARNING   = 4       #  warning conditions
    LOG_NOTICE    = 5       #  normal but significant condition
    LOG_INFO      = 6       #  informational
    LOG_DEBUG     = 7       #  debug-level messages

    #  facility codes
    LOG_KERN      = 0       #  kernel messages
    LOG_USER      = 1       #  random user-level messages
    LOG_MAIL      = 2       #  mail system
    LOG_DAEMON    = 3       #  system daemons
    LOG_AUTH      = 4       #  security/authorization messages
    LOG_SYSLOG    = 5       #  messages generated internally by syslogd
    LOG_LPR       = 6       #  line printer subsystem
    LOG_NEWS      = 7       #  network news subsystem
    LOG_UUCP      = 8       #  UUCP subsystem
    LOG_CRON      = 9       #  clock daemon
    LOG_AUTHPRIV  = 10      #  security/authorization messages (private)
    LOG_FTP       = 11      #  FTP daemon

    #  other codes through 15 reserved for system use
    LOG_LOCAL0    = 16      #  reserved for local use
    LOG_LOCAL1    = 17      #  reserved for local use
    LOG_LOCAL2    = 18      #  reserved for local use
    LOG_LOCAL3    = 19      #  reserved for local use
    LOG_LOCAL4    = 20      #  reserved for local use
    LOG_LOCAL5    = 21      #  reserved for local use
    LOG_LOCAL6    = 22      #  reserved for local use
    LOG_LOCAL7    = 23      #  reserved for local use

    priority_names = {
        "alert":    LOG_ALERT,
        "crit":     LOG_CRIT,
        "critical": LOG_CRIT,
        "debug":    LOG_DEBUG,
        "emerg":    LOG_EMERG,
        "err":      LOG_ERR,
        "error":    LOG_ERR,        #  DEPRECATED
        "info":     LOG_INFO,
        "notice":   LOG_NOTICE,
        "panic":    LOG_EMERG,      #  DEPRECATED
        "warn":     LOG_WARNING,    #  DEPRECATED
        "warning":  LOG_WARNING,
        }

    facility_names = {
        "auth":     LOG_AUTH,
        "authpriv": LOG_AUTHPRIV,
        "cron":     LOG_CRON,
        "daemon":   LOG_DAEMON,
        "ftp":      LOG_FTP,
        "kern":     LOG_KERN,
        "lpr":      LOG_LPR,
        "mail":     LOG_MAIL,
        "news":     LOG_NEWS,
        "security": LOG_AUTH,       #  DEPRECATED
        "syslog":   LOG_SYSLOG,
        "user":     LOG_USER,
        "uucp":     LOG_UUCP,
        "local0":   LOG_LOCAL0,
        "local1":   LOG_LOCAL1,
        "local2":   LOG_LOCAL2,
        "local3":   LOG_LOCAL3,
        "local4":   LOG_LOCAL4,
        "local5":   LOG_LOCAL5,
        "local6":   LOG_LOCAL6,
        "local7":   LOG_LOCAL7,
        }

    #The map below appears to be trivially lowercasing the key. However,
    #there's more to it than meets the eye - in some locales, lowercasing
    #gives unexpected results. See SF #1524081: in the Turkish locale,
    #"INFO".lower() != "info"
    priority_map = {
        "DEBUG": "debug",
        "INFO": "info",
        "WARNING": "warning",
        "ERROR": "error",
        "CRITICAL": "critical"
    }

    def __init__(self, address, port=SYSLOG_UDP_PORT, facility=LOG_USER, protocol=None):
        """
        Create a Syslog Handler. Must have a target syslog server. May specify port, protocol and logging facility.

        :param address:
        :param port:
        :param facility:
        """
        self.address = address
        self.port = port
        self.facility = facility

        if protocol is None:
            self._socktype = socket.SOCK_DGRAM
            self._conntype = socket._the_interface.UDP_MODE
        elif protocol.lower() == 'tcp':
            self._socktype = socket.SOCK_STREAM
            self._conntype = socket._the_interface.TCP_MODE
        else:
            self._socktype = socket.SOCK_DGRAM
            self._conntype = socket._the_interface.UDP_MODE

        self.socket = socket.socket(type=self._socktype)
        # Create a proper output socket. Key thing, the IP has to be byte-encoded.
        self._socketaddr_out = socket.getaddrinfo(self.address,self.port)[0][4]
        self.formatter = None

    def _close(self):
        self.socket.close()

    def _connect(self):
        self.socket.connect(self._socketaddr_out, conntype=self._conntype)

    def mapPriority(self, levelName):
        """
        Map a logging level name to a key in the priority_names map.
        This is useful in two scenarios: when custom levels are being
        used, and in the case where you can't do a straightforward
        mapping by lowercasing the logging level name because of locale-
        specific issues (see SF #1524081).
        """
        return self.priority_map.get(levelName, "warning")

    ident = ''          # prepended to all messages
    # Testing with rsyslogd 8.2102, and is required.
    append_nul = True  # some old syslog daemons expect a NUL terminator

    def emit(self, log_level: int, message: str):
        """
        Emit a record.

        The record is formatted, and then sent to the syslog server. If
        exception information is present, it is NOT sent to the server.
        """
        print("Received message: {}".format(message))
        msg = self.format(log_level, message)
        print("Formatted message: {}".format(msg))
        if self.ident:
            msg = self.ident + msg
        if self.append_nul:
            msg += '\000'

        # We need to convert record level to lowercase, maybe this will
        # change in the future.
        prio = '<%d>' % self.encodePriority(self.facility, self.mapPriority(log_level))
        prio = prio.encode('utf-8')
        # Message is a string. Convert to bytes as required by RFC 5424
        msg = msg.encode('utf-8')
        msg = prio + msg

        # Since the esp32spi_socket doesn't ever call beginPacket() again (see issue #135), we must
        # call connect and close every time.
        try:
            self._close()
            self._connect()
            self.socket.send(msg)
        except RuntimeError as e:
            print("--- LOGGING ERROR ---")
            print("With message: {}".format(message))
            traceback.print_exception(etype=type(e), value=e, tb=e.__traceback__)

    def encodePriority(self, facility, priority):
        """
        Encode the facility and priority. You can pass in strings or
        integers - if strings are passed, the facility_names and
        priority_names mapping dictionaries are used to convert them to
        integers.
        """
        if isinstance(facility, str):
            facility = self.facility_names[facility]
        if isinstance(priority, str):
            priority = self.priority_names[priority]
        return (facility << 3) | priority

    def format(self, log_level: int, message: str):
        """Generate a string to log

        :param log_level: The level of the message
        :param message: The message to format
        """
        return super().format(log_level, message)
