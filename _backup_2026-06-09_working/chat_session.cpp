#include "chat_session.h"
#include <QFile>
#include <QJsonDocument>
#include <QJsonObject>
#include <QDebug>

ChatSession::ChatSession(QObject *parent) : QObject(parent) {}

bool ChatSession::loadScenes(const QString &path)
{
    QFile f(path);
    if (!f.open(QIODevice::ReadOnly)) {
        qWarning() << "ChatSession: cannot open" << path;
        return false;
    }
    QJsonDocument doc = QJsonDocument::fromJson(f.readAll());
    f.close();
    QJsonArray arr = doc.object()["scenes"].toArray();
    m_scenes.clear();
    for (const QJsonValue &v : arr) {
        QJsonObject o = v.toObject();
        ChatScene s;
        s.id = o["id"].toString();
        s.title = o["title"].toString();
        s.titleCn = o["title_cn"].toString();
        s.icon = o["icon"].toString();
        s.color = o["color"].toString();
        s.systemPrompt = o["system_prompt"].toString();
        s.opening = o["opening"].toString();
        m_scenes.append(s);
    }
    qDebug() << "ChatSession: loaded" << m_scenes.size() << "scenes";
    return !m_scenes.isEmpty();
}

void ChatSession::selectScene(int idx)
{
    if (idx < 0 || idx >= m_scenes.size()) return;
    m_currentIdx = idx;
    m_history = QJsonArray();
    // Inject opening as the first AI turn so model knows context
    QJsonObject openMsg;
    openMsg["role"] = "assistant";
    openMsg["content"] = m_scenes[idx].opening;
    m_history.append(openMsg);
    setState(ChatState::AI_SPEAKING);
    emit sceneSelected(m_scenes[idx]);
    emit aiTurnAppended(m_scenes[idx].opening);
}

void ChatSession::exitScene()
{
    m_currentIdx = -1;
    m_history = QJsonArray();
    setState(ChatState::SCENE_SELECT);
}

void ChatSession::appendUserTurn(const QString &userText)
{
    QJsonObject msg;
    msg["role"] = "user";
    msg["content"] = userText;
    m_history.append(msg);
    emit userTurnAppended(userText);
}

void ChatSession::appendAiTurn(const QString &aiText)
{
    QJsonObject msg;
    msg["role"] = "assistant";
    msg["content"] = aiText;
    m_history.append(msg);
    emit aiTurnAppended(aiText);
}

void ChatSession::updateLastUserTurn(const QString &cleanedText)
{
    // Walk back to the most recent user message and replace its content.
    for (int i = m_history.size() - 1; i >= 0; --i) {
        QJsonObject msg = m_history.at(i).toObject();
        if (msg.value("role").toString() == "user") {
            msg["content"] = cleanedText;
            m_history.replace(i, msg);
            return;
        }
    }
}

void ChatSession::setState(ChatState s)
{
    if (m_state == s) return;
    m_state = s;
    emit stateChanged(s);
}
