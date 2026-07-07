#include "AiCloudClient.h"
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonArray>
#include <QBuffer>
#include <QDebug>

AiCloudClient::AiCloudClient(QObject *parent) : QObject(parent)
{
    m_manager = new QNetworkAccessManager(this);
    connect(m_manager, &QNetworkAccessManager::finished, this, &AiCloudClient::onReply);
}

void AiCloudClient::analyzeImage(const QImage &image)
{
    if (m_apiKey.isEmpty()) {
        emit analysisFailed("API Key not set");
        return;
    }
    if (image.isNull()) {
        emit analysisFailed("Camera frame is null");
        return;
    }

    QImage rgb = image.convertToFormat(QImage::Format_RGB888);
    QImage scaled = rgb.scaled(640, 640, Qt::KeepAspectRatio, Qt::SmoothTransformation);
    int w = scaled.width(), h = scaled.height();

    int rowSize = ((w * 3 + 3) / 4) * 4;
    int dataSize = rowSize * h;
    QByteArray bmp(14 + 40 + dataSize, 0);
    char *d = bmp.data();

    auto w32 = [](char *d, int pos, int v) { d[pos]=v; d[pos+1]=v>>8; d[pos+2]=v>>16; d[pos+3]=v>>24; };
    auto w16 = [](char *d, int pos, int v) { d[pos]=v; d[pos+1]=v>>8; };

    d[0]='B'; d[1]='M';
    w32(d, 2, 14+40+dataSize);
    w32(d, 10, 14+40);
    w32(d, 14, 40);
    w32(d, 18, w); w32(d, 22, h);
    w16(d, 26, 1);
    w16(d, 28, 24);

    const uchar *src = scaled.constBits();
    for (int y = 0; y < h; y++) {
        char *row = d + 54 + (h - 1 - y) * rowSize;
        for (int x = 0; x < w; x++) {
            int si = (y * w + x) * 3;
            row[x*3+0] = (char)src[si+2];
            row[x*3+1] = (char)src[si+1];
            row[x*3+2] = (char)src[si+0];
        }
    }

    if (bmp.size() < 100) {
        emit analysisFailed("BMP encode failed");
        return;
    }
    QString b64 = QString::fromLatin1(bmp.toBase64());

    QJsonArray content;
    QJsonObject imgPart;
    imgPart["type"] = "image_url";
    imgPart["image_url"] = QJsonObject{{"url", QString("data:image/bmp;base64,") + b64}};
    content.append(imgPart);

    QJsonObject textPart;
    textPart["type"] = "text";
    textPart["text"] = "Focus only on the object closest to the camera or being held up in the foreground. Ignore walls, floors, backgrounds, and patterns. What is that foreground object? Reply in JSON only: {\"word\": \"English noun\", \"cn\": \"中文\", \"phonetic\": \"/IPA/\", \"desc\": \"one English sentence\", \"desc_cn\": \"中文翻译\"}. No other text.";
    content.append(textPart);

    QJsonObject msg;
    msg["role"] = "user";
    msg["content"] = content;

    QJsonObject root;
    root["model"] = "qwen-vl-plus";
    root["messages"] = QJsonArray{msg};

    QNetworkRequest req(QUrl("https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    req.setRawHeader("Authorization", ("Bearer " + m_apiKey).toUtf8());

    QNetworkReply *reply = m_manager->post(req, QJsonDocument(root).toJson());
    reply->setProperty("type", "image");
    qDebug() << "Cloud API: sending" << bmp.size() << "bytes BMP";
}

void AiCloudClient::generateDailyReport(int totalMinutes, int wordCount, const QStringList &words)
{
    if (m_apiKey.isEmpty()) {
        emit dailyReportFailed("API Key not set");
        return;
    }

    QString wordList = words.isEmpty() ? "（今日暂无单词记录）" : words.join("、");
    QString prompt = QString(
        "你是一个英语学习助手。请根据以下今日学习数据，用中文写一段温暖有趣的学习日报（100字以内），"
        "可以鼓励学生，也可以根据学习时长给出建议。\n"
        "今日学习时长：%1 分钟\n"
        "今日学习单词数：%2 个\n"
        "今日学习单词：%3\n"
        "直接输出日报正文，不要加标题。"
    ).arg(totalMinutes).arg(wordCount).arg(wordList);

    QJsonObject msg;
    msg["role"] = "user";
    msg["content"] = prompt;

    QJsonObject root;
    root["model"] = "qwen-plus";
    root["messages"] = QJsonArray{msg};

    QNetworkRequest req(QUrl("https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    req.setRawHeader("Authorization", ("Bearer " + m_apiKey).toUtf8());

    QNetworkReply *reply = m_manager->post(req, QJsonDocument(root).toJson());
    reply->setProperty("type", "report");
    qDebug() << "Daily report: requesting for" << totalMinutes << "min," << wordCount << "words";
}

void AiCloudClient::chat(const QString &systemPrompt, const QJsonArray &history, const QString &userInput)
{
    if (m_apiKey.isEmpty()) {
        emit chatFailed("API Key not set");
        return;
    }

    QJsonArray messages;
    QJsonObject sysMsg;
    sysMsg["role"] = "system";
    // The user's text comes from on-device ASR which often mishears similar-sounding
    // words AND drops punctuation. Tell the LLM to (1) clean up the user's text
    // (punctuation, casing, obvious misrecognition fixes via scene context) AND
    // (2) generate a reply, returning BOTH as JSON. The UI then shows the cleaned
    // user text in the bubble so the user doesn't see ASR artifacts.
    QString asrHint =
        "\n\nIMPORTANT: The user's text comes from on-device ASR. It is missing "
        "punctuation/capitalization and may contain misheard words "
        "(e.g. 'bye now' transcribed as 'buy now', similar-sounding substitutions, "
        "garbled proper nouns). Your job:\n"
        "  1. Silently produce a CLEANED version of the user's text — fix "
        "punctuation, capitalization, and obvious misrecognitions using scene "
        "context. Preserve the user's intended meaning verbatim. Do NOT add "
        "content the user didn't say.\n"
        "  2. Generate a natural reply (under 15 words) to the cleaned input.\n"
        "Output STRICTLY this JSON object, no other text, no markdown fences:\n"
        "{\"u\": \"<cleaned user input>\", \"r\": \"<your reply>\"}\n"
        "Use plain ASCII punctuation only, no emoji.";
    sysMsg["content"] = systemPrompt + asrHint;
    messages.append(sysMsg);

    for (const QJsonValue &v : history)
        messages.append(v);

    if (!userInput.isEmpty()) {
        QJsonObject userMsg;
        userMsg["role"] = "user";
        userMsg["content"] = userInput;
        messages.append(userMsg);
    }

    QJsonObject root;
    root["model"] = "qwen-flash";
    root["messages"] = messages;

    QNetworkRequest req(QUrl("https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"));
    req.setHeader(QNetworkRequest::ContentTypeHeader, "application/json");
    req.setRawHeader("Authorization", ("Bearer " + m_apiKey).toUtf8());

    QNetworkReply *reply = m_manager->post(req, QJsonDocument(root).toJson());
    reply->setProperty("type", "chat");
    qDebug() << "Cloud chat: history=" << history.size() << "user=" << userInput.left(60);
}

void AiCloudClient::onReply(QNetworkReply *reply)
{
    QString replyType = reply->property("type").toString();

    if (reply->error() != QNetworkReply::NoError) {
        qWarning() << "Cloud API error:" << reply->errorString();
        if (replyType == "report")
            emit dailyReportFailed(reply->errorString());
        else if (replyType == "chat")
            emit chatFailed(reply->errorString());
        else
            emit analysisFailed(reply->errorString());
        reply->deleteLater();
        return;
    }

    QByteArray data = reply->readAll();
    reply->deleteLater();
    qDebug() << "Cloud API response:" << data.left(300);

    QJsonDocument doc = QJsonDocument::fromJson(data);
    QString content = doc.object()["choices"].toArray()[0]
                        .toObject()["message"].toObject()["content"].toString();

    if (replyType == "report") {
        if (content.isEmpty()) {
            emit dailyReportFailed("Empty response");
            return;
        }
        emit dailyReportReady(content.trimmed());
        return;
    }

    if (replyType == "chat") {
        if (content.isEmpty()) {
            emit chatFailed("Empty response");
            return;
        }
        // Expect {"u": "...", "r": "..."}. Be tolerant of markdown fences and
        // surrounding text by extracting the first {...} block. If parsing
        // fails, fall back to raw content as the reply with no correction.
        QString jsonText = content.trimmed();
        int b = jsonText.indexOf('{');
        int e = jsonText.lastIndexOf('}');
        QString correctedUser, aiReply;
        if (b >= 0 && e > b) {
            QJsonObject obj = QJsonDocument::fromJson(
                jsonText.mid(b, e - b + 1).toUtf8()).object();
            correctedUser = obj.value("u").toString().trimmed();
            aiReply       = obj.value("r").toString().trimmed();
        }
        if (aiReply.isEmpty()) {
            qWarning() << "chat reply not in JSON format, using raw:" << content.left(120);
            aiReply = content.trimmed();
            correctedUser = QString();   // empty -> caller keeps raw user text
        }
        emit chatReply(correctedUser, aiReply);
        return;
    }

    // image analysis
    int brace = content.indexOf('{');
    int endBrace = content.lastIndexOf('}');
    if (brace >= 0 && endBrace > brace)
        content = content.mid(brace, endBrace - brace + 1);

    QJsonObject result = QJsonDocument::fromJson(content.toUtf8()).object();
    QString word     = result["word"].toString();
    QString cn       = result["cn"].toString();
    QString phonetic = result["phonetic"].toString();
    QString desc     = result["desc"].toString();
    QString descCn   = result["desc_cn"].toString();

    if (word.isEmpty()) {
        emit analysisFailed("Failed to parse AI response: " + content);
        return;
    }

    emit analysisReady(word, cn, phonetic, desc, descCn);
}
