#include "uart_client.h"
#include <QDebug>
#include <fcntl.h>
#include <unistd.h>
#include <termios.h>
#include <sys/ioctl.h>
#include <cerrno>

UartClient::UartClient(const QString &device, int baudrate, QObject *parent)
    : QObject(parent)
{
    m_fd = open(device.toUtf8().constData(), O_RDWR | O_NOCTTY);
    if (m_fd < 0) {
        qWarning() << "UART: cannot open" << device;
        return;
    }

    struct termios opts;
    tcgetattr(m_fd, &opts);
    cfsetispeed(&opts, B115200);
    cfsetospeed(&opts, B115200);
    opts.c_cflag &= ~CSIZE;
    opts.c_cflag |= CS8 | CLOCAL | CREAD;
    opts.c_iflag = IGNPAR;
    opts.c_oflag = 0;
    opts.c_lflag = 0;
    opts.c_cc[VTIME] = 5;
    opts.c_cc[VMIN] = 1;
    tcsetattr(m_fd, TCSANOW, &opts);

    m_running = true;
    m_thread = QThread::create([this]() { readerLoop(); });
    m_thread->start();

    qDebug() << "UART opened:" << device;
}

UartClient::~UartClient()
{
    m_running = false;
    if (m_thread) {
        m_thread->wait(2000);
        delete m_thread;
    }
    if (m_fd >= 0) close(m_fd);
}

void UartClient::send(const QString &msg)
{
    if (m_fd < 0) return;
    QByteArray data = msg.toUtf8();
    write(m_fd, data.constData(), data.size());
}

void UartClient::readerLoop()
{
    char buf[256];
    QByteArray accum;
    int idle_ticks = 0;
    qDebug() << "UART readerLoop start fd=" << m_fd;
    while (m_running) {
        int n = read(m_fd, buf, sizeof(buf));
        if (n > 0) {
            qDebug() << "UART read n=" << n << "first16="
                     << QByteArray(buf, qMin(n, 16)).toHex();
            accum.append(buf, n);
            // emit complete '\n'-terminated lines; keep partial tail in accum
            int nl;
            while ((nl = accum.indexOf('\n')) >= 0) {
                QByteArray line = accum.left(nl);
                accum.remove(0, nl + 1);
                if (line.endsWith('\r')) line.chop(1);
                if (!line.isEmpty()) {
                    emit messageReceived(QString::fromUtf8(line));
                }
            }
            // safety: if accum grows unbounded (peer never sends \n), discard
            if (accum.size() > 8192) accum.clear();
            idle_ticks = 0;
        } else {
            if (++idle_ticks % 200 == 0) {
                qDebug() << "UART idle ticks=" << idle_ticks
                         << "last_read_n=" << n << "errno=" << errno;
            }
        }
        usleep(10000); // 10ms
    }
    qDebug() << "UART readerLoop exit";
}
