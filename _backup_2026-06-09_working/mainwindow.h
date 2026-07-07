#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QWidget>
#include <QStackedWidget>
#include <QLabel>
#include <QPushButton>
#include <QElapsedTimer>
#include <QTimer>
#include <QThread>
#include "camerawidget.h"
#include "uart_client.h"
#include "AiCloudClient.h"
#include "ai_engine.h"
#include "action_manager.h"
#include "study_session_manager.h"
#include "pet_emotion.h"
#include "chat_session.h"

class QScrollArea;

enum class AppState {
    IDLE,
    TRIGGERED,
    SPEAKING
};

#include <QResizeEvent>

class MainWindow : public QWidget
{
    Q_OBJECT
public:
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

protected:
    void resizeEvent(QResizeEvent *e) override;

private slots:
    void onEnterWordMode();
    void onEnterSpeakMode();
    void onCapturePhoto();
    void onAIDetected(const QString &wordEn, const QString &wordCn);
    void onBackToHome();
    void onUartMessage(const QString &msg);
    void onEcUartMessage(const QString &msg);
    void onSpeakWord();
    void onSpeakSentence();
    void onContinueScan();
    void onCloudAnalyze();
    void onScanAndIdentify();
    void onSpeakingTimeout();

    void onReadyToStart(const QString &wordEn, const QString &wordCn);
    void onLearningStarted(const QString &wordEn);
    void onLearningStopped(qint64 durationMs, const QString &content);
    void onStudyTick();
    void onCloudResult(const QString &wordEn, const QString &wordCn, const QString &phonetic, const QString &desc, const QString &descCn);
    void onCloudError(const QString &error);
    void onDailyReport();
    void onDailyReportReady(const QString &report);
    void onDailyReportFailed(const QString &error);
    void onBackFromReport();

    // Chat scene mode
    void onChatSceneSelected(int idx);
    void onChatRecordToggle();
    void onChatExit();
    void onChatReplyReady(const QString &correctedUser, const QString &aiReply);
    void onChatReplyFailed(const QString &error);
    void onChatUserText(const QString &text);   // user text from EC800M ASR
    void onChatSpeakDone();                     // EC800M finished speaking AI line

private:
    QStackedWidget *m_stack;
    CameraWidget *m_camera;
    UartClient *m_uart;
    UartClient *m_uartEC;
    QLabel *m_resultLabel;
    bool m_detecting = false;
    bool m_wordModeActive = false;
    QElapsedTimer m_detectTimer;

    AppState m_state = AppState::IDLE;
    void setState(AppState s);

    QWidget *m_cardPanel;
    QLabel *m_cardWordEn;
    QLabel *m_cardWordCn;
    QLabel *m_cardPhonetic;
    QLabel *m_cardConf;
    QLabel *m_cardDescCn;
    QPushButton *m_btnSpeakWord;
    QPushButton *m_btnSpeakSentence;
    QPushButton *m_btnContinue;
    QPushButton *m_btnCloudAnalyze;
    QPushButton *m_btnScanIdentify;

    QString m_lockedWordEn;
    QString m_lockedWordCn;
    QString m_lockedSentence;
    bool m_sentencePlaying = false;
    float m_lastConfidence = 0;
    int m_sameWordCount = 0;
    QString m_lastDetectedWord;

    QTimer *m_speakingTimer;

    ActionManager *m_actionMgr;
    StudySessionManager *m_studySession;
    AiCloudClient *m_cloudClient;
    AiEngine *m_ai;
    QThread *m_aiThread;
    PetEmotion *m_pet;

    QWidget *m_learningPanel;
    QLabel *m_timerLabel;
    QPushButton *m_btnStopLearning;
    QPushButton *m_btnStartLearning;
    QLabel *m_timerOverlay;   // floating timer shown on all pages
    QTimer *m_studyTickTimer;
    int m_currentSessionId = -1;

    QString lookupChinese(const QString &en);
    QString lookupPhonetic(const QString &en);
    void updatePetMood();
    void updateFatigue();
    void placePet();

    float m_fatigue = 0.0f;
    bool m_milestone10min = false;
    QStringList m_todayWords;
    QPushButton *m_btnDailyReport = nullptr;

    QLabel *m_reportText = nullptr;
    QLabel *m_reportWords = nullptr;
    QLabel *m_reportStats = nullptr;

    // ── Chat scene mode ─────────────────────────────────────
    ChatSession *m_chatSession = nullptr;
    QStackedWidget *m_chatInner = nullptr;     // 0=scene-select, 1=dialog
    QWidget *m_chatBubblesHost = nullptr;      // VBox for bubbles
    QScrollArea *m_chatScroll = nullptr;
    QLabel *m_chatTitle = nullptr;
    QLabel *m_chatStatus = nullptr;
    QPushButton *m_btnChatRecord = nullptr;
    QPushButton *m_btnChatExit = nullptr;
    bool m_chatRecording = false;
    QLabel *m_lastUserBubble = nullptr;   // tracked so onChatReplyReady can swap raw ASR for cleaned text

    void buildChatPage(QWidget *page);
    void appendChatBubble(const QString &text, bool isAi);
    void clearChatBubbles();
    void setChatStatus(const QString &text);
    static QString stripEmojiForTts(const QString &text);
};

#endif
