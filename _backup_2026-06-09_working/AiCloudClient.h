#ifndef AICLOUDCLIENT_H
#define AICLOUDCLIENT_H

#include <QObject>
#include <QNetworkAccessManager>
#include <QNetworkReply>
#include <QImage>
#include <QStringList>
#include <QJsonArray>

class AiCloudClient : public QObject {
    Q_OBJECT
public:
    explicit AiCloudClient(QObject *parent = nullptr);

    void setApiKey(const QString &key) { m_apiKey = key; }
    void analyzeImage(const QImage &image);
    void generateDailyReport(int totalMinutes, int wordCount, const QStringList &words);
    void chat(const QString &systemPrompt, const QJsonArray &history, const QString &userInput);

signals:
    void analysisReady(const QString &wordEn, const QString &wordCn, const QString &phonetic, const QString &desc, const QString &descCn);
    void analysisFailed(const QString &error);
    void dailyReportReady(const QString &report);
    void dailyReportFailed(const QString &error);
    void chatReply(const QString &correctedUser, const QString &aiReply);
    void chatFailed(const QString &error);

private slots:
    void onReply(QNetworkReply *reply);

private:
    QNetworkAccessManager *m_manager;
    QString m_apiKey;
    bool m_pendingReport = false;
};

#endif
