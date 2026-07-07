#ifndef UART_CLIENT_H
#define UART_CLIENT_H

#include <QObject>
#include <QThread>
#include <QByteArray>

class UartClient : public QObject
{
    Q_OBJECT
public:
    explicit UartClient(const QString &device, int baudrate,
                        QObject *parent = nullptr);
    ~UartClient();

    void send(const QString &msg);

signals:
    void messageReceived(const QString &msg);

private:
    int m_fd = -1;
    QThread *m_thread = nullptr;
    bool m_running = false;

    void readerLoop();
};

#endif // UART_CLIENT_H
