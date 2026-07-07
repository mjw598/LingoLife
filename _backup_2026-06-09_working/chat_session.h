#ifndef CHAT_SESSION_H
#define CHAT_SESSION_H

#include <QObject>
#include <QString>
#include <QVector>
#include <QJsonArray>

struct ChatScene {
    QString id;
    QString title;
    QString titleCn;
    QString icon;
    QString color;
    QString systemPrompt;
    QString opening;
};

enum class ChatState {
    SCENE_SELECT,   // 场景选择中
    AI_SPEAKING,    // AI 正在说话（等 EC800M 播完）
    USER_RECORDING, // 用户录音中
    AI_THINKING,    // 等待云端回复
    IDLE_WAIT       // AI 说完，等用户按录音
};

class ChatSession : public QObject
{
    Q_OBJECT
public:
    explicit ChatSession(QObject *parent = nullptr);

    bool loadScenes(const QString &path);
    const QVector<ChatScene> &scenes() const { return m_scenes; }
    const ChatScene *currentScene() const { return m_currentIdx >= 0 ? &m_scenes[m_currentIdx] : nullptr; }

    void selectScene(int idx);
    void exitScene();

    void appendUserTurn(const QString &userText);
    void appendAiTurn(const QString &aiText);
    void updateLastUserTurn(const QString &cleanedText);  // swap raw ASR for LLM-cleaned form

    QJsonArray history() const { return m_history; }

    ChatState state() const { return m_state; }
    void setState(ChatState s);

signals:
    void stateChanged(ChatState s);
    void userTurnAppended(const QString &text);
    void aiTurnAppended(const QString &text);
    void sceneSelected(const ChatScene &scene);

private:
    QVector<ChatScene> m_scenes;
    int m_currentIdx = -1;
    QJsonArray m_history;          // OpenAI-format messages (excluding system)
    ChatState m_state = ChatState::SCENE_SELECT;
};

#endif
