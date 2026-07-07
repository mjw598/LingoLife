#include "mainwindow.h"
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QDebug>
#include <QMap>
#include <QScrollArea>
#include <QScrollBar>
#include <QFrame>

// ── COCO 80 labels -> Chinese + Phonetic lookup ──────────────────
static QMap<QString, QPair<QString, QString>> makeWordMap()
{
    QMap<QString, QPair<QString, QString>> m;
    //         English          Chinese       Phonetic
    m["person"]        = {"人",          "/ˈpɜːrsn/"};
    m["bicycle"]       = {"自行车",       "/ˈbaɪsɪkl/"};
    m["car"]           = {"汽车",         "/kɑːr/"};
    m["motorcycle"]    = {"摩托车",       "/ˈmoʊtərsaɪkl/"};
    m["airplane"]      = {"飞机",         "/ˈerpleɪn/"};
    m["bus"]           = {"公共汽车",     "/bʌs/"};
    m["train"]         = {"火车",         "/treɪn/"};
    m["truck"]         = {"卡车",         "/trʌk/"};
    m["boat"]          = {"船",           "/boʊt/"};
    m["traffic light"] = {"交通灯",       "/ˈtræfɪk laɪt/"};
    m["fire hydrant"]  = {"消防栓",       "/ˈfaɪər ˈhaɪdrənt/"};
    m["stop sign"]     = {"停止标志",     "/stɑːp saɪn/"};
    m["parking meter"] = {"停车计时器",   "/ˈpɑːrkɪŋ ˈmiːtər/"};
    m["bench"]         = {"长凳",         "/bentʃ/"};
    m["bird"]          = {"鸟",           "/bɜːrd/"};
    m["cat"]           = {"猫",           "/kæt/"};
    m["dog"]           = {"狗",           "/dɔːɡ/"};
    m["horse"]         = {"马",           "/hɔːrs/"};
    m["sheep"]         = {"羊",           "/ʃiːp/"};
    m["cow"]           = {"牛",           "/kaʊ/"};
    m["elephant"]      = {"大象",         "/ˈelɪfənt/"};
    m["bear"]          = {"熊",           "/ber/"};
    m["zebra"]         = {"斑马",         "/ˈziːbrə/"};
    m["giraffe"]       = {"长颈鹿",       "/dʒɪˈræf/"};
    m["backpack"]      = {"背包",         "/ˈbækpæk/"};
    m["umbrella"]      = {"雨伞",         "/ʌmˈbrelə/"};
    m["handbag"]       = {"手提包",       "/ˈhændbæɡ/"};
    m["tie"]           = {"领带",         "/taɪ/"};
    m["suitcase"]      = {"手提箱",       "/ˈsuːtkeɪs/"};
    m["frisbee"]       = {"飞盘",         "/ˈfrɪzbiː/"};
    m["skis"]          = {"滑雪板",       "/skiːz/"};
    m["snowboard"]     = {"滑雪板",       "/ˈsnoʊbɔːrd/"};
    m["sports ball"]   = {"运动球",       "/spɔːrts bɔːl/"};
    m["kite"]          = {"风筝",         "/kaɪt/"};
    m["baseball bat"]  = {"棒球棒",       "/ˈbeɪsbɔːl bæt/"};
    m["baseball glove"]= {"棒球手套",     "/ˈbeɪsbɔːl ɡlʌv/"};
    m["skateboard"]    = {"滑板",         "/ˈskeɪtbɔːrd/"};
    m["surfboard"]     = {"冲浪板",       "/ˈsɜːrfbɔːrd/"};
    m["tennis racket"] = {"网球拍",       "/ˈtenɪs ˈrækɪt/"};
    m["bottle"]        = {"瓶子",         "/ˈbɑːtl/"};
    m["wine glass"]    = {"酒杯",         "/waɪn ɡlæs/"};
    m["cup"]           = {"杯子",         "/kʌp/"};
    m["fork"]          = {"叉子",         "/fɔːrk/"};
    m["knife"]         = {"刀",           "/naɪf/"};
    m["spoon"]         = {"勺子",         "/spuːn/"};
    m["bowl"]          = {"碗",           "/boʊl/"};
    m["banana"]        = {"香蕉",         "/bəˈnænə/"};
    m["apple"]         = {"苹果",         "/ˈæpl/"};
    m["sandwich"]      = {"三明治",       "/ˈsænwɪtʃ/"};
    m["orange"]        = {"橙子",         "/ˈɔːrɪndʒ/"};
    m["broccoli"]      = {"西兰花",       "/ˈbrɑːkəli/"};
    m["carrot"]        = {"胡萝卜",       "/ˈkærət/"};
    m["hot dog"]       = {"热狗",         "/hɑːt dɔːɡ/"};
    m["pizza"]         = {"披萨",         "/ˈpiːtsə/"};
    m["donut"]         = {"甜甜圈",       "/ˈdoʊnʌt/"};
    m["cake"]          = {"蛋糕",         "/keɪk/"};
    m["chair"]         = {"椅子",         "/tʃer/"};
    m["couch"]         = {"沙发",         "/kaʊtʃ/"};
    m["potted plant"]  = {"盆栽",         "/ˈpɑːtɪd plænt/"};
    m["bed"]           = {"床",           "/bed/"};
    m["dining table"]  = {"餐桌",         "/ˈdaɪnɪŋ ˈteɪbl/"};
    m["toilet"]        = {"马桶",         "/ˈtɔɪlɪt/"};
    m["tv"]            = {"电视",         "/ˌtiː ˈviː/"};
    m["laptop"]        = {"笔记本电脑",   "/ˈlæptɑːp/"};
    m["mouse"]         = {"鼠标",         "/maʊs/"};
    m["remote"]        = {"遥控器",       "/rɪˈmoʊt/"};
    m["keyboard"]      = {"键盘",         "/ˈkiːbɔːrd/"};
    m["cell phone"]    = {"手机",         "/sel foʊn/"};
    m["microwave"]     = {"微波炉",       "/ˈmaɪkrəweɪv/"};
    m["oven"]          = {"烤箱",         "/ˈʌvn/"};
    m["toaster"]       = {"烤面包机",     "/ˈtoʊstər/"};
    m["sink"]          = {"水槽",         "/sɪŋk/"};
    m["refrigerator"]  = {"冰箱",         "/rɪˈfrɪdʒəreɪtər/"};
    m["book"]          = {"书",           "/bʊk/"};
    m["clock"]         = {"时钟",         "/klɑːk/"};
    m["vase"]          = {"花瓶",         "/veɪs/"};
    m["scissors"]      = {"剪刀",         "/ˈsɪzərz/"};
    m["teddy bear"]    = {"泰迪熊",       "/ˈtedi ber/"};
    m["hair drier"]    = {"吹风机",       "/her ˈdraɪər/"};
    m["toothbrush"]    = {"牙刷",         "/ˈtuːθbrʌʃ/"};
    return m;
}

static QMap<QString, QPair<QString, QString>> wordMap = makeWordMap();

QString MainWindow::lookupChinese(const QString &en)
{
    auto it = wordMap.find(en);
    return it != wordMap.end() ? it->first : en;
}

QString MainWindow::lookupPhonetic(const QString &en)
{
    auto it = wordMap.find(en);
    return it != wordMap.end() ? it->second : "";
}

// ── State Machine ───────────────────────────────────────────────

void MainWindow::setState(AppState s)
{
    if (m_state == s) return;
    AppState prev = m_state;
    m_state = s;
    qDebug() << "State:" << (int)prev << "->" << (int)s;

    switch (s) {
    case AppState::IDLE:
        m_detecting = false;
        m_detectTimer.invalidate();
        m_resultLabel->setText("");
        m_resultLabel->show();
        m_cardPanel->hide();
        m_btnScanIdentify->setEnabled(true);
        m_lockedSentence.clear();
        m_btnSpeakSentence->hide();
        // Resume real-time detection
        break;

    case AppState::TRIGGERED:
        m_camera->clearTracks();
        m_resultLabel->hide();
        m_cardPanel->show();
        m_cardWordEn->setText(m_lockedWordEn);
        m_cardWordCn->setText(m_lockedWordCn);
        m_cardPhonetic->setText(lookupPhonetic(m_lockedWordEn));
        m_cardConf->setText(QString("%1%").arg((int)(m_lastConfidence * 100)));
        m_btnSpeakWord->setEnabled(true);
        m_btnSpeakWord->setText("Listen Word");
        m_btnSpeakSentence->setEnabled(true);
        m_btnSpeakSentence->setText("Listen Sentence");
        m_btnSpeakSentence->setVisible(!m_lockedSentence.isEmpty());
        m_btnContinue->setEnabled(true);
        m_sentencePlaying = false;
        // Show cloud analyze button when confidence is low
        m_btnCloudAnalyze->setVisible(m_lastConfidence < 0.60f);
        // Send to EC800M
        {
            QString cmd = QString("WORD:%1:%2\n").arg(m_lockedWordEn, m_lockedWordCn);
            m_uart->send(cmd);
            m_uartEC->send(cmd);
        }
        break;

    case AppState::SPEAKING:
        m_btnSpeakWord->setEnabled(false);
        m_btnSpeakSentence->setEnabled(false);
        m_btnContinue->setEnabled(false);
        if (m_sentencePlaying) {
            m_btnSpeakSentence->setText("Playing...");
        } else {
            m_btnSpeakWord->setText("Playing...");
        }
        m_speakingTimer->start(8000); // timeout 8s
        break;
    }
}

// ── Constructor ─────────────────────────────────────────────────

MainWindow::MainWindow(QWidget *parent) : QWidget(parent)
{
    m_camera = new CameraWidget(this);
    m_uart = new UartClient("/dev/ttyS1", 115200, this);
    m_uartEC = new UartClient("/dev/ttyS8", 115200, this);

    // ── Learning system (ActionManager + SQLite + Pet) ─────
    m_actionMgr = new ActionManager(this);
    m_studySession = new StudySessionManager("/data/study.json", this);
    m_cloudClient = new AiCloudClient(this);
    m_cloudClient->setApiKey("sk-6bfcca7f0f484e429ce29770ec0774d5");

    m_chatSession = new ChatSession(this);
    if (!m_chatSession->loadScenes("/data/scenes.json"))
        m_chatSession->loadScenes("scenes.json");
    connect(m_cloudClient, &AiCloudClient::chatReply, this, &MainWindow::onChatReplyReady);
    connect(m_cloudClient, &AiCloudClient::chatFailed, this, &MainWindow::onChatReplyFailed);

    m_ai = new AiEngine;
    m_aiThread = new QThread(this);
    m_ai->moveToThread(m_aiThread);
    m_aiThread->start();
    connect(m_ai, &AiEngine::detected, this, &MainWindow::onAIDetected);
    connect(m_camera, &CameraWidget::frameReady, m_ai, &AiEngine::detect, Qt::QueuedConnection);
    m_camera->setAiBusyFlag(m_ai->busyFlag());
    m_pet = new PetEmotion(this);
    m_pet->setVisiblePet(true);

    // Floating timer overlay — top-left corner, visible on all pages while learning
    m_timerOverlay = new QLabel("00:00:00", this);
    m_timerOverlay->setFixedSize(180, 44);
    m_timerOverlay->setAlignment(Qt::AlignCenter);
    m_timerOverlay->setStyleSheet(
        "background:rgba(44,62,80,180);color:#7BC8D3;font-size:22px;font-weight:bold;"
        "border-radius:22px;padding:0 12px;");
    m_timerOverlay->move(12, 12);
    m_timerOverlay->hide();
    m_timerOverlay->raise();

    // m_timerLabel kept as alias so existing slots compile
    m_timerLabel = m_timerOverlay;

    placePet();

    m_studyTickTimer = new QTimer(this);
    connect(m_studyTickTimer, &QTimer::timeout, this, &MainWindow::onStudyTick);

    connect(m_actionMgr, &ActionManager::readyToStart, this, &MainWindow::onReadyToStart);
    connect(m_actionMgr, &ActionManager::learningStarted, this, &MainWindow::onLearningStarted);
    connect(m_actionMgr, &ActionManager::learningStopped, this, &MainWindow::onLearningStopped);
    connect(m_cloudClient, &AiCloudClient::analysisReady, this, &MainWindow::onCloudResult);
    connect(m_cloudClient, &AiCloudClient::analysisFailed, this, &MainWindow::onCloudError);
    connect(m_cloudClient, &AiCloudClient::dailyReportReady, this, &MainWindow::onDailyReportReady);
    connect(m_cloudClient, &AiCloudClient::dailyReportFailed, this, &MainWindow::onDailyReportFailed);

    m_speakingTimer = new QTimer(this);
    m_speakingTimer->setSingleShot(true);
    connect(m_speakingTimer, &QTimer::timeout, this, &MainWindow::onSpeakingTimeout);

    m_stack = new QStackedWidget(this);

    // ── page 0: Home ────────────────────────────────────────
    QWidget *home = new QWidget;
    home->setStyleSheet("background:#F9F7F2;font-family:'DejaVu Sans','Arial',sans-serif;");
    QVBoxLayout *hl = new QVBoxLayout(home);
    hl->setAlignment(Qt::AlignCenter);
    hl->setSpacing(28);
    hl->setContentsMargins(50, 50, 50, 50);

    QLabel *icon = new QLabel(QString::fromUtf8("🎓"));
    icon->setAlignment(Qt::AlignCenter);
    icon->setFixedSize(120, 120);
    icon->setStyleSheet(
        "background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #F5C842,stop:1 #F19672);"
        "color:white;font-size:60px;font-weight:bold;border-radius:60px;");

    QLabel *title = new QLabel("AI English Tutor");
    title->setAlignment(Qt::AlignCenter);
    title->setStyleSheet("color:#2C3E50;font-size:50px;font-weight:bold;background:transparent;");

    QLabel *subtitle = new QLabel("English Learning Assistant");
    subtitle->setAlignment(Qt::AlignCenter);
    subtitle->setStyleSheet("color:#7F8C8D;font-size:24px;background:transparent;");

    QLabel *sub = new QLabel("Discover Point & Learn  |  Elevate AI Speaking");
    sub->setAlignment(Qt::AlignCenter);
    sub->setStyleSheet("color:#95A5A6;font-size:18px;background:transparent;padding:8px;");

    // Make cards clickable via QPushButton with embedded layout
    QPushButton *btnCardWord = new QPushButton;
    btnCardWord->setMinimumSize(680, 140);
    btnCardWord->setMaximumSize(680, 140);
    btnCardWord->setStyleSheet(
        "QPushButton{background:#EBF8FA;border-radius:20px;border:2px solid #B2E4EA;text-align:left;padding-left:28px;}"
        "QPushButton:pressed{background:#D4F0F5;border-color:#7BC8D3;}");
    QHBoxLayout *bcwl = new QHBoxLayout(btnCardWord);
    bcwl->setContentsMargins(28, 20, 28, 20);
    bcwl->setSpacing(20);
    QLabel *camIcon2 = new QLabel(QString::fromUtf8("📷"));
    camIcon2->setFixedSize(64, 64);
    camIcon2->setAlignment(Qt::AlignCenter);
    camIcon2->setStyleSheet("background:#7BC8D3;color:white;font-size:32px;font-weight:bold;border-radius:32px;");
    QVBoxLayout *bcwText = new QVBoxLayout;
    QLabel *bcwTitle = new QLabel("Discover & Learn");
    bcwTitle->setStyleSheet("color:#2C3E50;font-size:28px;font-weight:bold;background:transparent;");
    QLabel *bcwDesc = new QLabel("Word Identification & Learning");
    bcwDesc->setStyleSheet("color:#7F8C8D;font-size:18px;background:transparent;");
    bcwText->addWidget(bcwTitle);
    bcwText->addWidget(bcwDesc);
    bcwl->addWidget(camIcon2);
    bcwl->addLayout(bcwText);
    bcwl->addStretch();

    QPushButton *btnCardSpeak = new QPushButton;
    btnCardSpeak->setMinimumSize(680, 140);
    btnCardSpeak->setMaximumSize(680, 140);
    btnCardSpeak->setStyleSheet(
        "QPushButton{background:#FEF0EB;border-radius:20px;border:2px solid #F9C9B8;text-align:left;padding-left:28px;}"
        "QPushButton:pressed{background:#FDDDD0;border-color:#F19672;}");
    QHBoxLayout *bcsl = new QHBoxLayout(btnCardSpeak);
    bcsl->setContentsMargins(28, 20, 28, 20);
    bcsl->setSpacing(20);
    QLabel *micIcon2 = new QLabel(QString::fromUtf8("🎤"));
    micIcon2->setFixedSize(64, 64);
    micIcon2->setAlignment(Qt::AlignCenter);
    micIcon2->setStyleSheet("background:#F19672;color:white;font-size:32px;font-weight:bold;border-radius:32px;");
    QVBoxLayout *bcsText = new QVBoxLayout;
    QLabel *bcsTitle = new QLabel("Speak & Practice");
    bcsTitle->setStyleSheet("color:#2C3E50;font-size:28px;font-weight:bold;background:transparent;");
    QLabel *bcsDesc = new QLabel("Interactive Speaking Practice");
    bcsDesc->setStyleSheet("color:#7F8C8D;font-size:18px;background:transparent;");
    bcsText->addWidget(bcsTitle);
    bcsText->addWidget(bcsDesc);
    bcsl->addWidget(micIcon2);
    bcsl->addLayout(bcsText);
    bcsl->addStretch();

    hl->addStretch();
    hl->addWidget(icon, 0, Qt::AlignCenter);
    hl->addWidget(title);
    hl->addWidget(subtitle);
    hl->addWidget(sub);
    hl->addSpacing(10);
    hl->addWidget(btnCardWord, 0, Qt::AlignCenter);
    hl->addWidget(btnCardSpeak, 0, Qt::AlignCenter);
    hl->addSpacing(10);

    // ── Learning start/stop on home page ──
    QHBoxLayout *homeLearnRow = new QHBoxLayout;
    m_btnStartLearning = new QPushButton("开始学习");
    m_btnStartLearning->setMinimumSize(260, 64);
    m_btnStartLearning->setStyleSheet(
        "QPushButton{background:#52C878;color:white;font-size:22px;font-weight:bold;"
        "border-radius:32px;border:none;}"
        "QPushButton:pressed{background:#3DAA5C;}");
    m_btnStartLearning->setCursor(Qt::PointingHandCursor);

    m_btnStopLearning = new QPushButton("结束学习");
    m_btnStopLearning->setMinimumSize(260, 64);
    m_btnStopLearning->setStyleSheet(
        "QPushButton{background:#E74C3C;color:white;font-size:22px;font-weight:bold;"
        "border-radius:32px;border:none;}"
        "QPushButton:pressed{background:#C0392B;}");
    m_btnStopLearning->setCursor(Qt::PointingHandCursor);
    m_btnStopLearning->hide();

    homeLearnRow->addStretch();
    homeLearnRow->addWidget(m_btnStartLearning);
    homeLearnRow->addSpacing(20);
    homeLearnRow->addWidget(m_btnStopLearning);
    homeLearnRow->addStretch();
    hl->addLayout(homeLearnRow);
    hl->addStretch();

    // Daily report button at bottom of home
    m_btnDailyReport = new QPushButton("今日日报");
    m_btnDailyReport->setMinimumSize(200, 56);
    m_btnDailyReport->setStyleSheet(
        "QPushButton{background:#F5C842;color:#2C3E50;font-size:20px;font-weight:bold;"
        "border-radius:28px;border:none;}"
        "QPushButton:pressed{background:#D4A820;}");
    m_btnDailyReport->setCursor(Qt::PointingHandCursor);
    hl->addWidget(m_btnDailyReport, 0, Qt::AlignCenter);
    hl->addSpacing(16);

    connect(btnCardWord, &QPushButton::clicked, this, &MainWindow::onEnterWordMode);
    connect(btnCardSpeak, &QPushButton::clicked, this, &MainWindow::onEnterSpeakMode);
    connect(m_btnDailyReport, &QPushButton::clicked, this, &MainWindow::onDailyReport);
    connect(m_btnStartLearning, &QPushButton::clicked, m_actionMgr, &ActionManager::onStartLearning);
    connect(m_btnStopLearning, &QPushButton::clicked, m_actionMgr, &ActionManager::onStopLearning);

    // ── page 1: Word Mode ────────────────────────────────────
    QWidget *wordPage = new QWidget;
    wordPage->setStyleSheet("background:#F9F7F2;");
    QVBoxLayout *wl = new QVBoxLayout(wordPage);
    wl->setContentsMargins(0, 0, 0, 0);
    wl->setSpacing(0);

    // Camera
    m_camera->setSizePolicy(QSizePolicy::Expanding, QSizePolicy::Expanding);

    // ── Learning Card Panel ──
    m_cardPanel = new QWidget;
    m_cardPanel->setFixedHeight(260);
    m_cardPanel->setStyleSheet("background:#F9F7F2;border-top:2px solid #E8E4DC;");
    m_cardPanel->hide();

    QVBoxLayout *cardLayout = new QVBoxLayout(m_cardPanel);
    cardLayout->setContentsMargins(16, 10, 16, 10);
    cardLayout->setSpacing(4);

    QHBoxLayout *topRow = new QHBoxLayout;
    m_cardWordEn = new QLabel("---");
    m_cardWordEn->setStyleSheet("color:#2C3E50;font-size:32px;font-weight:bold;background:transparent;");
    topRow->addWidget(m_cardWordEn);
    topRow->addStretch();

    QHBoxLayout *midRow = new QHBoxLayout;
    m_cardWordCn = new QLabel("---");
    m_cardWordCn->setStyleSheet("color:#F19672;font-size:24px;font-weight:bold;background:transparent;");
    m_cardPhonetic = new QLabel("");
    m_cardPhonetic->setStyleSheet("color:#7F8C8D;font-size:18px;background:transparent;");
    midRow->addWidget(m_cardWordCn);
    midRow->addSpacing(16);
    midRow->addWidget(m_cardPhonetic);
    midRow->addStretch();

    m_cardConf = new QLabel("");
    m_cardConf->setStyleSheet("color:#5D6D7E;font-size:14px;background:transparent;");
    m_cardConf->setWordWrap(true);

    QHBoxLayout *btnRow = new QHBoxLayout;
    btnRow->setSpacing(8);
    m_btnSpeakWord = new QPushButton("Listen Word");
    m_btnSpeakWord->setMinimumSize(0, 56);
    m_btnSpeakWord->setStyleSheet(
        "QPushButton{background:#7BC8D3;color:white;font-size:16px;font-weight:bold;"
        "border-radius:28px;border:none;padding:0 8px;}"
        "QPushButton:pressed{background:#5AABB8;}"
        "QPushButton:disabled{background:#C8E6EA;color:#A0C4C9;}");
    m_btnSpeakWord->setCursor(Qt::PointingHandCursor);

    m_btnSpeakSentence = new QPushButton("Listen Sentence");
    m_btnSpeakSentence->setMinimumSize(0, 56);
    m_btnSpeakSentence->setStyleSheet(
        "QPushButton{background:#7BC8D3;color:white;font-size:16px;font-weight:bold;"
        "border-radius:28px;border:none;padding:0 8px;}"
        "QPushButton:pressed{background:#5AABB8;}"
        "QPushButton:disabled{background:#C8E6EA;color:#A0C4C9;}");
    m_btnSpeakSentence->setCursor(Qt::PointingHandCursor);
    m_btnSpeakSentence->hide();

    m_btnContinue = new QPushButton("Capture");
    m_btnContinue->setMinimumSize(0, 56);
    m_btnContinue->setStyleSheet(
        "QPushButton{background:#F19672;color:white;font-size:16px;font-weight:bold;"
        "border-radius:28px;border:none;padding:0 8px;}"
        "QPushButton:pressed{background:#D97A5A;}"
        "QPushButton:disabled{background:#F9C9B8;color:#E8A090;}");
    m_btnContinue->setCursor(Qt::PointingHandCursor);

    m_btnCloudAnalyze = new QPushButton("AI");
    m_btnCloudAnalyze->setMinimumSize(0, 56);
    m_btnCloudAnalyze->setStyleSheet(
        "QPushButton{background:#9B59B6;color:white;font-size:16px;font-weight:bold;"
        "border-radius:28px;border:none;padding:0 8px;}"
        "QPushButton:pressed{background:#7D3C98;}");
    m_btnCloudAnalyze->setCursor(Qt::PointingHandCursor);
    m_btnCloudAnalyze->hide();

    btnRow->addWidget(m_btnSpeakWord, 1);
    btnRow->addWidget(m_btnSpeakSentence, 1);
    btnRow->addWidget(m_btnCloudAnalyze, 1);
    btnRow->addWidget(m_btnContinue, 1);

    connect(m_btnCloudAnalyze, &QPushButton::clicked, this, &MainWindow::onCloudAnalyze);

    cardLayout->addLayout(topRow);
    cardLayout->addLayout(midRow);
    cardLayout->addWidget(m_cardConf);

    m_cardDescCn = new QLabel("");
    m_cardDescCn->setStyleSheet("color:#5D6D7E;font-size:16px;background:transparent;");
    m_cardDescCn->setWordWrap(true);
    cardLayout->addWidget(m_cardDescCn);

    cardLayout->addLayout(btnRow);

    // ── Learning session row removed from card — now on home page ──

    connect(m_btnSpeakWord, &QPushButton::clicked, this, &MainWindow::onSpeakWord);
    connect(m_btnSpeakSentence, &QPushButton::clicked, this, &MainWindow::onSpeakSentence);
    connect(m_btnContinue, &QPushButton::clicked, this, &MainWindow::onContinueScan);

    wl->addWidget(m_camera, 1);
    wl->addWidget(m_cardPanel, 0);

    // Bottom bar
    QWidget *bar = new QWidget;
    bar->setFixedHeight(88);
    bar->setStyleSheet("background:#F9F7F2;border-top:1px solid #E8E4DC;");
    QHBoxLayout *bl = new QHBoxLayout(bar);
    bl->setContentsMargins(16, 8, 16, 8);

    QPushButton *btnBack = new QPushButton("Back");
    btnBack->setMinimumSize(110, 56);
    btnBack->setStyleSheet(
        "QPushButton{color:#7F8C8D;font-size:18px;background:transparent;"
        "border:2px solid #BDC3C7;border-radius:28px;padding:0 16px;font-weight:bold;}"
        "QPushButton:pressed{background:#ECF0F1;}");
    btnBack->setCursor(Qt::PointingHandCursor);

    m_btnScanIdentify = new QPushButton("Scan & Identify");
    m_btnScanIdentify->setMinimumSize(220, 56);
    m_btnScanIdentify->setStyleSheet(
        "QPushButton{background:#7BC8D3;color:white;font-size:18px;font-weight:bold;"
        "border-radius:28px;border:none;padding:0 16px;}"
        "QPushButton:pressed{background:#5AABB8;}"
        "QPushButton:disabled{background:#C8E6EA;color:#A0C4C9;}");
    m_btnScanIdentify->setCursor(Qt::PointingHandCursor);
    QPushButton *btnCapture = m_btnScanIdentify;

    m_resultLabel = new QLabel("");
    m_resultLabel->setAlignment(Qt::AlignCenter);
    m_resultLabel->setStyleSheet("color:#2C3E50;font-size:18px;font-weight:bold;background:transparent;");

    bl->addWidget(btnBack);
    bl->addStretch();
    bl->addWidget(m_resultLabel);
    bl->addStretch();
    bl->addWidget(btnCapture);
    wl->addWidget(bar);

    connect(btnBack, &QPushButton::clicked, this, &MainWindow::onBackToHome);
    connect(btnCapture, &QPushButton::clicked, this, &MainWindow::onScanAndIdentify);

    // ── page 2: Chat Mode (Scene-based dialog) ────────────────
    QWidget *speakPage = new QWidget;
    buildChatPage(speakPage);

    m_stack->addWidget(home);
    m_stack->addWidget(wordPage);
    m_stack->addWidget(speakPage);

    // ── page 3: Daily Report ──────────────────────────────────
    QWidget *reportPage = new QWidget;
    reportPage->setStyleSheet("background:#F9F7F2;");
    QVBoxLayout *rl = new QVBoxLayout(reportPage);
    rl->setContentsMargins(40, 30, 40, 30);
    rl->setSpacing(16);

    QLabel *rTitle = new QLabel("今日学习日报");
    rTitle->setAlignment(Qt::AlignCenter);
    rTitle->setStyleSheet("color:#2C3E50;font-size:32px;font-weight:bold;background:transparent;");

    m_reportStats = new QLabel("");
    m_reportStats->setAlignment(Qt::AlignCenter);
    m_reportStats->setStyleSheet(
        "color:#7F8C8D;font-size:20px;background:rgba(255,255,255,180);"
        "border-radius:12px;padding:10px;border:1px solid #E0DDD5;");

    m_reportText = new QLabel("");
    m_reportText->setWordWrap(true);
    m_reportText->setAlignment(Qt::AlignLeft | Qt::AlignTop);
    m_reportText->setStyleSheet(
        "color:#2C3E50;font-size:22px;background:rgba(255,255,255,200);"
        "border-radius:16px;padding:18px;border:1px solid #E0DDD5;");

    m_reportWords = new QLabel("");
    m_reportWords->setWordWrap(true);
    m_reportWords->setAlignment(Qt::AlignLeft | Qt::AlignTop);
    m_reportWords->setStyleSheet(
        "color:#F19672;font-size:20px;font-weight:bold;background:rgba(255,248,240,200);"
        "border-radius:16px;padding:16px;border:1px solid #F9C9B8;");

    QPushButton *btnBackReport = new QPushButton("返回主页");
    btnBackReport->setMinimumSize(240, 64);
    btnBackReport->setStyleSheet(
        "QPushButton{background:#F19672;color:white;font-size:22px;font-weight:bold;"
        "border-radius:32px;border:none;}"
        "QPushButton:pressed{background:#D97A5A;}");
    btnBackReport->setCursor(Qt::PointingHandCursor);

    rl->addWidget(rTitle);
    rl->addWidget(m_reportStats);
    rl->addWidget(m_reportText, 1);
    rl->addWidget(m_reportWords);
    rl->addStretch();
    rl->addWidget(btnBackReport, 0, Qt::AlignCenter);

    connect(btnBackReport, &QPushButton::clicked, this, &MainWindow::onBackFromReport);

    m_stack->addWidget(reportPage);

    QVBoxLayout *mainLayout = new QVBoxLayout(this);
    mainLayout->setContentsMargins(0, 0, 0, 0);
    mainLayout->addWidget(m_stack);
    m_stack->setCurrentIndex(0);

    // No YOLOv5 detection — camera frames only used for display and manual capture
    connect(m_uart, &UartClient::messageReceived, this, &MainWindow::onUartMessage);
    connect(m_uartEC, &UartClient::messageReceived, this, &MainWindow::onEcUartMessage);
}

MainWindow::~MainWindow() {
    m_aiThread->quit();
    m_aiThread->wait();
    delete m_ai;
}

// ── Events / State Transitions ───────────────────────────────────

void MainWindow::onEnterWordMode() {
    m_wordModeActive = true;
    m_detecting = false;
    m_detectTimer.invalidate();
    m_lastDetectedWord.clear();
    m_sameWordCount = 0;
    updatePetMood();
    setState(AppState::IDLE);
    m_detecting = true;
    QMetaObject::invokeMethod(m_ai, [this](){
        if (!m_ai->loadModel("/data/yolov5s_qsm368zp.rknn"))
            qWarning() << "Failed to load RKNN model";
    }, Qt::QueuedConnection);
    m_camera->start("/dev/video-camera0", 640, 480);
    m_stack->setCurrentIndex(1);
}

void MainWindow::onEnterSpeakMode() {
    m_uart->send("MODE:CHAT\n");
    m_uartEC->send("MODE:CHAT\n");
    if (m_chatInner) m_chatInner->setCurrentIndex(0);
    m_chatSession->exitScene();
    m_stack->setCurrentIndex(2);
}

void MainWindow::onScanAndIdentify()
{
    if (m_state == AppState::SPEAKING) return;
    m_state = AppState::IDLE;
    m_detecting = false;  // block YOLO label updates
    m_cardPanel->hide();
    m_resultLabel->show();
    QImage frame = m_camera->captureFrame();
    if (frame.isNull()) {
        m_resultLabel->setText("No frame");
        return;
    }
    m_resultLabel->setText("Identifying...");
    m_btnScanIdentify->setEnabled(false);
    m_cloudClient->analyzeImage(frame);
}

void MainWindow::onCapturePhoto() {
    if (m_state != AppState::IDLE) return;
    if (m_lastDetectedWord.isEmpty()) {
        m_resultLabel->setText("No object detected");
        return;
    }
    m_lockedWordEn = m_lastDetectedWord;
    m_lockedWordCn = lookupChinese(m_lastDetectedWord);
    if (!m_todayWords.contains(m_lockedWordEn))
        m_todayWords.append(m_lockedWordEn);
    qDebug() << "Manual trigger on:" << m_lockedWordEn;
    setState(AppState::TRIGGERED);
}

void MainWindow::onAIDetected(const QString &wordEn, const QString &wordCn) {
    if (m_state != AppState::IDLE || !m_detecting) return;

    if (wordEn.isEmpty() || wordEn == "Model not loaded" || wordEn == "Error") {
        m_lastDetectedWord.clear();
        m_resultLabel->setText("");
        return;
    }

    // Show detection label only — no auto-trigger, user presses Scan & Identify
    m_lastDetectedWord = wordEn;
    m_resultLabel->setText(wordEn + "  " + lookupChinese(wordEn));
    m_actionMgr->onObjectDetected(wordEn);
}

void MainWindow::onSpeakWord() {
    qDebug() << "[BTN] onSpeakWord clicked";
    if (m_state != AppState::TRIGGERED) return;
    QString cmd = QString("SPEAK:%1\n").arg(m_lockedWordEn);
    m_uart->send(cmd);
    m_uartEC->send(cmd);
    m_sentencePlaying = false;
    setState(AppState::SPEAKING);
}

void MainWindow::onSpeakSentence() {
    qDebug() << "[BTN] onSpeakSentence clicked, sentence=" << m_lockedSentence;
    if (m_state != AppState::TRIGGERED) return;
    if (m_lockedSentence.isEmpty()) return;
    QString cleanSentence = m_lockedSentence;
    cleanSentence.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ');
    cleanSentence = cleanSentence.simplified();
    QString cmd = QString("SPEAK:%1\n").arg(cleanSentence);
    qDebug() << "[BTN] sending cmd bytes=" << cmd.toUtf8().toHex() << "raw=" << cmd;
    m_uart->send(cmd);
    m_uartEC->send(cmd);
    m_sentencePlaying = true;
    setState(AppState::SPEAKING);
}

void MainWindow::onContinueScan() {
    if (m_actionMgr->isLearning())
        m_actionMgr->onStopLearning();
    m_lastDetectedWord.clear();
    m_sameWordCount = 0;
    m_studyTickTimer->stop();
    setState(AppState::IDLE);
}

void MainWindow::onSpeakingTimeout() {
    qDebug() << "Speaking timeout";
    if (m_state == AppState::SPEAKING) {
        m_state = AppState::TRIGGERED;
        m_btnSpeakWord->setEnabled(true);
        m_btnSpeakWord->setText("Listen Word");
        m_btnSpeakSentence->setEnabled(true);
        m_btnSpeakSentence->setText("Listen Sentence");
        m_btnContinue->setEnabled(true);
        m_sentencePlaying = false;
    }
}

void MainWindow::onBackToHome() {
    m_wordModeActive = false;
    m_detecting = false;
    m_lastDetectedWord.clear();
    m_sameWordCount = 0;
    m_speakingTimer->stop();
    setState(AppState::IDLE);
    m_camera->clearTracks();
    m_camera->stop();
    m_stack->setCurrentIndex(0);
}

void MainWindow::onCloudAnalyze()
{
    QImage frame = m_camera->captureFrame();
    if (frame.isNull()) return;

    m_cardConf->setText("Analyzing...");
    m_btnCloudAnalyze->setEnabled(false);
    m_btnSpeakWord->setEnabled(false);
    m_btnContinue->setEnabled(false);

    m_cloudClient->analyzeImage(frame);
}

void MainWindow::onCloudResult(const QString &wordEn, const QString &wordCn, const QString &phonetic, const QString &desc, const QString &descCn)
{
    qDebug() << "Cloud result:" << wordEn << wordCn << phonetic << desc;
    m_detecting = true;
    m_btnScanIdentify->setEnabled(true);
    m_resultLabel->setText("");

    m_lockedWordEn = wordEn;
    m_lockedWordCn = wordCn.isEmpty() ? wordEn : wordCn;

    if (!m_todayWords.contains(wordEn)) {
        m_todayWords.append(wordEn);
        if (m_todayWords.size() == 1)
            m_pet->showBubble("学了第一个单词！棒棒的！", 3000);
    }

    if (m_state == AppState::IDLE) {
        setState(AppState::TRIGGERED);
    }

    m_cardWordEn->setText(wordEn);
    m_cardWordCn->setText(m_lockedWordCn);
    // Use cloud phonetic if available, fallback to lookup table
    QString ph = phonetic.isEmpty() ? lookupPhonetic(wordEn) : phonetic;
    m_cardPhonetic->setText(ph);
    m_cardConf->setText(desc.isEmpty() ? "AI analyzed" : desc);
    m_cardDescCn->setText(descCn);
    m_lockedSentence = desc;
    m_btnSpeakSentence->setVisible(!desc.isEmpty());
    m_btnCloudAnalyze->hide();
    m_btnCloudAnalyze->setEnabled(true);
    m_btnSpeakWord->setEnabled(true);
    m_btnContinue->setEnabled(true);
}

void MainWindow::onCloudError(const QString &error)
{
    qWarning() << "Cloud error:" << error;
    m_detecting = true;
    m_btnScanIdentify->setEnabled(true);
    m_resultLabel->setText("");
    m_cardConf->setText("AI error: " + error);
    m_btnCloudAnalyze->setEnabled(true);
    m_btnSpeakWord->setEnabled(true);
    m_btnContinue->setEnabled(true);
}

void MainWindow::onUartMessage(const QString &msg) {
    qDebug() << "UART recv:" << msg;

    // Handle cloud vision result (via EC800M, kept for backward compat)
    if (msg.startsWith("VISION_RESULT:")) {
        QString json = msg.mid(14);
        // Parse: {"word":"apple","cn":"苹果","desc":"This is a red apple..."}
        // Simple string split for no JSON parser
        auto extract = [&](const QString &key) -> QString {
            int start = json.indexOf(QString("\"%1\":\"").arg(key));
            if (start < 0) return "";
            start += key.size() + 4;
            int end = json.indexOf("\"", start);
            if (end < 0) return "";
            return json.mid(start, end - start);
        };
        QString cloudWord = extract("word");
        QString cloudCn   = extract("cn");
        QString cloudDesc = extract("desc");

        if (!cloudWord.isEmpty()) {
            m_cardWordEn->setText(cloudWord);
            m_lockedWordEn = cloudWord;
        }
        if (!cloudCn.isEmpty()) {
            m_cardWordCn->setText(cloudCn);
            m_lockedWordCn = cloudCn;
        }
        if (!cloudDesc.isEmpty()) {
            m_cardConf->setText(cloudDesc);
            m_lockedSentence = cloudDesc;
            m_btnSpeakSentence->show();
        } else {
            m_cardConf->setText("AI analyzed");
        }
        m_btnCloudAnalyze->hide();
        m_btnCloudAnalyze->setEnabled(true);
        return;
    }

    if (msg.startsWith("TTS:DONE") || msg.startsWith("SPEAK:DONE")) {
        if (m_state == AppState::SPEAKING) {
            m_speakingTimer->stop();
            setState(AppState::TRIGGERED);
        }
    } else if (msg.startsWith("ASR:")) {
        QLabel *dl = m_stack->widget(2)->findChild<QLabel*>("dialogLabel");
        if (dl) dl->setText(msg.mid(4));
    } else {
        QLabel *dl = m_stack->widget(2)->findChild<QLabel*>("dialogLabel");
        if (dl) dl->setText(msg);
    }
}

// ── Learning Session Slots ───────────────────────────────────────

void MainWindow::onReadyToStart(const QString &wordEn, const QString &wordCn)
{
    Q_UNUSED(wordEn); Q_UNUSED(wordCn);
}

void MainWindow::onLearningStarted(const QString &wordEn)
{
    qDebug() << "LEARNING:" << wordEn;
    m_currentSessionId = m_studySession->startSession(wordEn);

    m_btnStartLearning->hide();
    m_btnStopLearning->show();
    m_timerLabel->setText("00:00:00");
    m_timerLabel->show();
    m_timerLabel->raise();
    m_studyTickTimer->start(1000);
    m_milestone10min = false;

    m_pet->cheer();
    updatePetMood();
}

void MainWindow::onLearningStopped(qint64 durationMs, const QString &content)
{
    qDebug() << "LEARNING STOPPED:" << content << durationMs << "ms";
    m_studyTickTimer->stop();
    m_btnStopLearning->hide();
    m_btnStartLearning->show();
    m_timerLabel->hide();

    if (m_currentSessionId >= 0) {
        m_studySession->endSession(m_currentSessionId);
        m_currentSessionId = -1;
    }
    updatePetMood();
}

void MainWindow::onStudyTick()
{
    if (m_actionMgr->isLearning()) {
        m_timerLabel->setText(m_actionMgr->elapsedString());
        if (!m_milestone10min && m_actionMgr->elapsedMs() >= 10 * 60 * 1000) {
            m_milestone10min = true;
            m_pet->cheer();
            m_pet->showBubble("坚持10分钟了！继续加油！", 4000);
        }
    }
    updateFatigue();
}

void MainWindow::updatePetMood()
{
    // fatigue drives pet appearance; also update label with today's stats
    m_pet->setFatigue((int)m_fatigue);
}

void MainWindow::updateFatigue()
{
    float prev = m_fatigue;
    if (m_actionMgr->isLearning()) {
        m_fatigue = qMin(100.0f, m_fatigue + 0.056f);
    } else {
        m_fatigue = qMax(0.0f, m_fatigue - 0.028f);
    }
    if (prev < 75.0f && m_fatigue >= 75.0f)
        m_pet->showBubble("有点累了，休息一下吧~", 5000);
    m_pet->setFatigue((int)m_fatigue);
}

void MainWindow::placePet()
{
    // position pet at bottom-right, raised above all widgets
    int x = width() - m_pet->width() - 8;
    int y = height() - m_pet->height() - 28;
    m_pet->move(x, y);
    m_pet->raise();
}

void MainWindow::resizeEvent(QResizeEvent *e)
{
    QWidget::resizeEvent(e);
    placePet();
}

void MainWindow::onDailyReport()
{
    int minutes = m_studySession->todayTotalMinutes();
    int wordCount = m_todayWords.size();
    m_btnDailyReport->setEnabled(false);
    m_btnDailyReport->setText("生成中...");
    m_cloudClient->generateDailyReport(minutes, wordCount, m_todayWords);
}

void MainWindow::onDailyReportReady(const QString &report)
{
    m_btnDailyReport->setEnabled(true);
    m_btnDailyReport->setText("今日日报");

    int minutes = m_studySession->todayTotalMinutes();
    int wordCount = m_todayWords.size();
    m_reportStats->setText(QString("今日学习时长：%1 分钟   |   今日单词数：%2 个")
                           .arg(minutes).arg(wordCount));
    m_reportText->setText(report);

    QString wordLine = m_todayWords.isEmpty()
        ? "（今日暂无单词记录）"
        : "今日单词：" + m_todayWords.join("  /  ");
    m_reportWords->setText(wordLine);

    m_stack->setCurrentIndex(3);
    m_pet->cheer();
}

void MainWindow::onDailyReportFailed(const QString &error)
{
    m_btnDailyReport->setEnabled(true);
    m_btnDailyReport->setText("今日日报");
    m_pet->showBubble("日报生成失败: " + error, 5000);
}

void MainWindow::onBackFromReport()
{
    m_stack->setCurrentIndex(0);
}

// ── Chat Scene Mode ──────────────────────────────────────────────

void MainWindow::buildChatPage(QWidget *page)
{
    page->setStyleSheet("background:#1B2A4A;");
    QVBoxLayout *root = new QVBoxLayout(page);
    root->setContentsMargins(0, 0, 0, 0);
    root->setSpacing(0);

    m_chatInner = new QStackedWidget(page);
    root->addWidget(m_chatInner);

    // ── Inner page 0: Scene picker ──
    QWidget *picker = new QWidget;
    QVBoxLayout *pl = new QVBoxLayout(picker);
    pl->setContentsMargins(40, 40, 40, 40);
    pl->setSpacing(20);

    QLabel *pTitle = new QLabel("Choose a Scene");
    pTitle->setAlignment(Qt::AlignCenter);
    pTitle->setStyleSheet("color:white;font-size:42px;font-weight:bold;background:transparent;");

    QLabel *pSub = new QLabel("Pick a scenario and chat with the AI in English");
    pSub->setAlignment(Qt::AlignCenter);
    pSub->setStyleSheet("color:rgba(180,200,255,180);font-size:20px;background:transparent;");

    pl->addWidget(pTitle);
    pl->addWidget(pSub);
    pl->addSpacing(10);

    // Scene cards in a 2-col grid
    QWidget *gridHost = new QWidget;
    QVBoxLayout *gridLay = new QVBoxLayout(gridHost);
    gridLay->setSpacing(16);
    gridLay->setContentsMargins(0, 0, 0, 0);

    const auto &scenes = m_chatSession->scenes();
    QHBoxLayout *currentRow = nullptr;
    for (int i = 0; i < scenes.size(); i++) {
        if (i % 2 == 0) {
            currentRow = new QHBoxLayout;
            currentRow->setSpacing(16);
            gridLay->addLayout(currentRow);
        }
        const ChatScene &s = scenes[i];
        QPushButton *card = new QPushButton;
        card->setMinimumSize(330, 110);
        card->setMaximumSize(400, 110);
        card->setCursor(Qt::PointingHandCursor);
        card->setStyleSheet(QString(
            "QPushButton{background:rgba(255,255,255,12);border-radius:18px;"
            "border:2px solid %1;text-align:left;padding:14px;}"
            "QPushButton:pressed{background:rgba(255,255,255,28);}").arg(s.color));
        QHBoxLayout *cl = new QHBoxLayout(card);
        cl->setContentsMargins(14, 8, 14, 8);
        cl->setSpacing(14);
        QLabel *icon = new QLabel(s.icon);
        icon->setFixedSize(60, 60);
        icon->setAlignment(Qt::AlignCenter);
        icon->setStyleSheet(QString(
            "background:%1;border-radius:30px;font-size:32px;").arg(s.color));
        QVBoxLayout *txt = new QVBoxLayout;
        txt->setSpacing(2);
        QLabel *t1 = new QLabel(s.title);
        t1->setStyleSheet("color:white;font-size:20px;font-weight:bold;background:transparent;");
        QLabel *t2 = new QLabel(s.titleCn);
        t2->setStyleSheet("color:rgba(200,220,255,180);font-size:15px;background:transparent;");
        txt->addWidget(t1);
        txt->addWidget(t2);
        cl->addWidget(icon);
        cl->addLayout(txt);
        cl->addStretch();
        currentRow->addWidget(card);
        connect(card, &QPushButton::clicked, this, [this, i]() { onChatSceneSelected(i); });
    }
    if (scenes.size() % 2 == 1 && currentRow)
        currentRow->addStretch();

    pl->addWidget(gridHost);
    pl->addStretch();

    QPushButton *btnBackHub = new QPushButton("Back to Hub");
    btnBackHub->setMinimumSize(280, 64);
    btnBackHub->setStyleSheet(
        "QPushButton{background:transparent;color:rgba(200,220,255,200);font-size:20px;"
        "font-weight:bold;border:2px solid rgba(123,200,211,150);border-radius:32px;}"
        "QPushButton:pressed{background:rgba(123,200,211,20);}");
    btnBackHub->setCursor(Qt::PointingHandCursor);
    pl->addWidget(btnBackHub, 0, Qt::AlignCenter);
    connect(btnBackHub, &QPushButton::clicked, this, &MainWindow::onBackToHome);

    m_chatInner->addWidget(picker);

    // ── Inner page 1: Dialog view ──
    QWidget *dlg = new QWidget;
    QVBoxLayout *dl = new QVBoxLayout(dlg);
    dl->setContentsMargins(20, 20, 20, 20);
    dl->setSpacing(12);

    QHBoxLayout *topRow = new QHBoxLayout;
    m_chatTitle = new QLabel("Scene");
    m_chatTitle->setStyleSheet("color:white;font-size:28px;font-weight:bold;background:transparent;");
    m_btnChatExit = new QPushButton("Exit");
    m_btnChatExit->setMinimumSize(100, 44);
    m_btnChatExit->setCursor(Qt::PointingHandCursor);
    m_btnChatExit->setStyleSheet(
        "QPushButton{background:transparent;color:rgba(200,220,255,200);font-size:18px;"
        "font-weight:bold;border:2px solid rgba(123,200,211,150);border-radius:22px;}"
        "QPushButton:pressed{background:rgba(123,200,211,20);}");
    topRow->addWidget(m_chatTitle);
    topRow->addStretch();
    topRow->addWidget(m_btnChatExit);
    dl->addLayout(topRow);

    m_chatScroll = new QScrollArea;
    m_chatScroll->setWidgetResizable(true);
    m_chatScroll->setHorizontalScrollBarPolicy(Qt::ScrollBarAlwaysOff);
    m_chatScroll->setStyleSheet(
        "QScrollArea{background:rgba(255,255,255,8);border-radius:18px;"
        "border:1px solid rgba(123,200,211,60);}");
    m_chatBubblesHost = new QWidget;
    m_chatBubblesHost->setStyleSheet("background:transparent;");
    QVBoxLayout *bvl = new QVBoxLayout(m_chatBubblesHost);
    bvl->setContentsMargins(16, 16, 16, 16);
    bvl->setSpacing(10);
    bvl->addStretch();
    m_chatScroll->setWidget(m_chatBubblesHost);
    dl->addWidget(m_chatScroll, 1);

    m_chatStatus = new QLabel("Tap to record");
    m_chatStatus->setAlignment(Qt::AlignCenter);
    m_chatStatus->setStyleSheet(
        "color:rgba(200,220,255,220);font-size:18px;background:transparent;padding:6px;");
    dl->addWidget(m_chatStatus);

    m_btnChatRecord = new QPushButton("🎤 Tap to Speak");
    m_btnChatRecord->setMinimumSize(0, 80);
    m_btnChatRecord->setCursor(Qt::PointingHandCursor);
    m_btnChatRecord->setStyleSheet(
        "QPushButton{background:#F19672;color:white;font-size:24px;font-weight:bold;"
        "border-radius:40px;border:none;}"
        "QPushButton:pressed{background:#D97A5A;}"
        "QPushButton:disabled{background:#888;color:#ccc;}");
    dl->addWidget(m_btnChatRecord);

    connect(m_btnChatRecord, &QPushButton::clicked, this, &MainWindow::onChatRecordToggle);
    connect(m_btnChatExit, &QPushButton::clicked, this, &MainWindow::onChatExit);

    m_chatInner->addWidget(dlg);
    m_chatInner->setCurrentIndex(0);
}

void MainWindow::appendChatBubble(const QString &text, bool isAi)
{
    if (!m_chatBubblesHost) return;
    QVBoxLayout *bvl = qobject_cast<QVBoxLayout*>(m_chatBubblesHost->layout());
    if (!bvl) return;

    QLabel *bubble = new QLabel(text);
    bubble->setWordWrap(true);
    bubble->setMaximumWidth(560);
    bubble->setStyleSheet(isAi
        ? "background:rgba(123,200,211,60);color:white;font-size:20px;"
          "padding:12px 16px;border-radius:14px;border:1px solid rgba(123,200,211,120);"
        : "background:rgba(241,150,114,80);color:white;font-size:20px;"
          "padding:12px 16px;border-radius:14px;border:1px solid rgba(241,150,114,140);");

    QHBoxLayout *row = new QHBoxLayout;
    row->setContentsMargins(0, 0, 0, 0);
    if (isAi) {
        row->addWidget(bubble);
        row->addStretch();
    } else {
        row->addStretch();
        row->addWidget(bubble);
        m_lastUserBubble = bubble;   // remember so we can swap text after LLM cleanup
    }
    bvl->insertLayout(bvl->count() - 1, row);  // before the trailing stretch

    // scroll to bottom
    QTimer::singleShot(50, [this]() {
        if (m_chatScroll)
            m_chatScroll->verticalScrollBar()->setValue(m_chatScroll->verticalScrollBar()->maximum());
    });
}

void MainWindow::clearChatBubbles()
{
    m_lastUserBubble = nullptr;
    if (!m_chatBubblesHost) return;
    QVBoxLayout *bvl = qobject_cast<QVBoxLayout*>(m_chatBubblesHost->layout());
    if (!bvl) return;
    while (bvl->count() > 1) {  // keep trailing stretch
        QLayoutItem *it = bvl->takeAt(0);
        if (!it) break;
        if (QLayout *child = it->layout()) {
            // Detach widgets so deleteLater (Qt event loop) handles them safely
            // instead of QLayoutItem dtor deleting them under us. Don't manually
            // `delete child` — `delete it` already cascades to the layout.
            while (QLayoutItem *ci = child->takeAt(0)) {
                if (QWidget *w = ci->widget()) w->deleteLater();
                delete ci;
            }
        }
        delete it;
    }
}

void MainWindow::setChatStatus(const QString &text)
{
    if (m_chatStatus) m_chatStatus->setText(text);
}

QString MainWindow::stripEmojiForTts(const QString &text)
{
    QString out;
    out.reserve(text.size());
    for (int i = 0; i < text.size(); ) {
        uint cp;
        QChar c = text.at(i);
        if (c.isHighSurrogate() && i + 1 < text.size() && text.at(i + 1).isLowSurrogate()) {
            cp = QChar::surrogateToUcs4(c, text.at(i + 1));
            i += 2;
        } else {
            cp = c.unicode();
            i += 1;
        }
        // Drop ranges that Baidu TTS reads as words: emoji + pictographs + dingbats + symbols
        bool drop =
            (cp >= 0x1F300 && cp <= 0x1FAFF) ||  // Misc Symbols/Pictographs, Emoticons, Transport, Supplemental Symbols/Pictographs, Symbols & Pictographs Extended-A
            (cp >= 0x2600  && cp <= 0x27BF)  ||  // Misc Symbols + Dingbats
            (cp >= 0x1F1E6 && cp <= 0x1F1FF) ||  // Regional indicator (flags)
            (cp >= 0xFE00  && cp <= 0xFE0F)  ||  // Variation selectors
            cp == 0x200D                     ||  // ZWJ
            cp == 0x20E3;                        // Combining enclosing keycap
        if (drop) continue;
        // Map "fancy" punctuation that Baidu TTS reads literally (e.g. "left
        // double quotation mark") to plain ASCII equivalents
        switch (cp) {
            case 0x2018: case 0x2019: case 0x201A: case 0x201B: cp = '\''; break;  // ' ' ‚ ‛
            case 0x201C: case 0x201D: case 0x201E: case 0x201F: cp = '"';  break;  // " " „ ‟
            case 0x2013: case 0x2014: case 0x2015: cp = '-';  break;               // – — ―
            case 0x2026: out.append("..."); continue;                              // …
            case 0x2022: case 0x00B7: cp = ' '; break;                             // • ·
            case 0x00A0: cp = ' '; break;                                          // NBSP
            default: break;
        }
        if (cp > 0xFFFF) {
            out.append(QChar::highSurrogate(cp));
            out.append(QChar::lowSurrogate(cp));
        } else {
            out.append(QChar(cp));
        }
    }
    return out.simplified();
}

void MainWindow::onChatSceneSelected(int idx)
{
    clearChatBubbles();
    m_chatSession->selectScene(idx);
    const ChatScene *s = m_chatSession->currentScene();
    if (!s) return;
    m_chatTitle->setText(QString("%1 %2").arg(s->icon).arg(s->title));
    m_chatInner->setCurrentIndex(1);
    appendChatBubble(s->opening, true);
    setChatStatus("AI is speaking...");
    m_btnChatRecord->setEnabled(false);
    m_btnChatRecord->setText("🔊 AI Speaking...");
    QString cmd = QString("SPEAK:%1\n").arg(stripEmojiForTts(s->opening));
    m_uartEC->send(cmd);
    // Without DONE feedback yet, estimate by length
    int durMs = qMax(2500, s->opening.length() * 80);
    QTimer::singleShot(durMs, this, &MainWindow::onChatSpeakDone);
}

void MainWindow::onChatRecordToggle()
{
    if (!m_chatRecording) {
        m_chatRecording = true;
        m_btnChatRecord->setText("⏹ Tap to Stop");
        m_btnChatRecord->setStyleSheet(
            "QPushButton{background:#E74C3C;color:white;font-size:24px;font-weight:bold;"
            "border-radius:40px;border:none;}"
            "QPushButton:pressed{background:#C0392B;}");
        setChatStatus("Recording... speak now");
        m_uartEC->send("RECORD:START\n");
    } else {
        m_chatRecording = false;
        m_btnChatRecord->setEnabled(false);
        m_btnChatRecord->setText("⏳ Recognizing...");
        m_btnChatRecord->setStyleSheet(
            "QPushButton{background:#888;color:#ccc;font-size:24px;font-weight:bold;"
            "border-radius:40px;border:none;}");
        setChatStatus("Recognizing speech...");
        m_uartEC->send("RECORD:STOP\n");
        m_chatSession->setState(ChatState::AI_THINKING);
    }
}

void MainWindow::onChatExit()
{
    m_chatRecording = false;
    m_chatSession->exitScene();
    if (m_chatInner) m_chatInner->setCurrentIndex(0);
    m_uartEC->send("MODE:IDLE\n");
    m_stack->setCurrentIndex(0);
}

void MainWindow::onChatUserText(const QString &text)
{
    QString clean = text.trimmed();
    if (clean.isEmpty()) {
        setChatStatus("Didn't catch that — tap to try again");
        m_btnChatRecord->setEnabled(true);
        m_btnChatRecord->setText("🎤 Tap to Speak");
        m_btnChatRecord->setStyleSheet(
            "QPushButton{background:#F19672;color:white;font-size:24px;font-weight:bold;"
            "border-radius:40px;border:none;}"
            "QPushButton:pressed{background:#D97A5A;}");
        return;
    }
    appendChatBubble(clean, false);
    m_chatSession->appendUserTurn(clean);

    setChatStatus("AI is thinking...");
    const ChatScene *s = m_chatSession->currentScene();
    if (!s) return;
    // chat() expects history without the latest user turn (it appends it)
    QJsonArray hist = m_chatSession->history();
    // remove the last entry (the user turn we just appended) since chat() will add it back
    if (!hist.isEmpty()) hist.removeLast();
    m_cloudClient->chat(s->systemPrompt, hist, clean);
}

void MainWindow::onChatReplyReady(const QString &correctedUser, const QString &aiReply)
{
    qDebug() << "onChatReplyReady enter, corrected len=" << correctedUser.size()
             << "reply len=" << aiReply.size();
    if (!m_chatSession || !m_btnChatRecord || !m_uartEC) {
        qWarning() << "onChatReplyReady: critical pointer null, ignoring";
        return;
    }
    if (m_chatSession->state() == ChatState::SCENE_SELECT) return;

    // Swap the last user bubble to the cleaned text if LLM provided one
    // (and it actually differs from what we already showed).
    if (!correctedUser.isEmpty() && m_lastUserBubble) {
        QString prev = m_lastUserBubble->text();
        if (correctedUser != prev) {
            m_lastUserBubble->setText(correctedUser);
            qDebug() << "user bubble cleaned:" << prev << "->" << correctedUser;
            m_chatSession->updateLastUserTurn(correctedUser);
        }
    }

    QString clean = aiReply.trimmed();
    if (clean.isEmpty()) clean = "Sorry, could you say that again?";
    m_chatSession->appendAiTurn(clean);
    qDebug() << "onChatReplyReady: appended ai turn";
    appendChatBubble(clean, true);
    qDebug() << "onChatReplyReady: bubble added";

    setChatStatus("AI is speaking...");
    m_btnChatRecord->setEnabled(false);
    m_btnChatRecord->setText("🔊 AI Speaking...");
    m_btnChatRecord->setStyleSheet(
        "QPushButton{background:#888;color:#ccc;font-size:24px;font-weight:bold;"
        "border-radius:40px;border:none;}");

    QString line = clean;
    line.replace('\n', ' ');
    line = stripEmojiForTts(line);
    m_uartEC->send(QString("SPEAK:%1\n").arg(line));
    int durMs = qMax(2500, clean.length() * 80);
    QTimer::singleShot(durMs, this, &MainWindow::onChatSpeakDone);
    qDebug() << "onChatReplyReady: scheduled speak-done in" << durMs << "ms";
}

void MainWindow::onChatReplyFailed(const QString &error)
{
    qWarning() << "Chat reply failed:" << error;
    setChatStatus("Network error — tap to try again");
    m_btnChatRecord->setEnabled(true);
    m_btnChatRecord->setText("🎤 Tap to Speak");
    m_btnChatRecord->setStyleSheet(
        "QPushButton{background:#F19672;color:white;font-size:24px;font-weight:bold;"
        "border-radius:40px;border:none;}"
        "QPushButton:pressed{background:#D97A5A;}");
}

void MainWindow::onChatSpeakDone()
{
    if (m_chatSession->state() == ChatState::SCENE_SELECT) return;
    setChatStatus("Tap to speak your reply");
    m_btnChatRecord->setEnabled(true);
    m_btnChatRecord->setText("🎤 Tap to Speak");
    m_btnChatRecord->setStyleSheet(
        "QPushButton{background:#F19672;color:white;font-size:24px;font-weight:bold;"
        "border-radius:40px;border:none;}"
        "QPushButton:pressed{background:#D97A5A;}");
    m_chatSession->setState(ChatState::IDLE_WAIT);
}

void MainWindow::onEcUartMessage(const QString &msg)
{
    qDebug() << "EC RX:" << msg;
    if (msg.startsWith("LOG:")) {
        qDebug() << "  [EC800M]" << msg.mid(4);
        return;
    }
    // chat-page widgets may not be built yet if EC800M sends early
    if (!m_btnChatRecord || !m_chatSession) {
        qDebug() << "  ignored (chat UI not ready)";
        return;
    }
    if (msg.startsWith("USER:")) {
        QString text = msg.mid(5).trimmed();
        onChatUserText(text);
    } else if (msg.startsWith("ASR:ERR")) {
        onChatUserText("");  // empty -> retry prompt
    } else if (msg.startsWith("RECORD:VAD")) {
        // EC800M auto-stopped after detecting end-of-speech silence.
        // Mirror the manual-stop UI transition; don't send RECORD:STOP back.
        if (m_chatRecording) {
            m_chatRecording = false;
            m_btnChatRecord->setEnabled(false);
            m_btnChatRecord->setText("⏳ Recognizing...");
            m_btnChatRecord->setStyleSheet(
                "QPushButton{background:#888;color:#ccc;font-size:24px;font-weight:bold;"
                "border-radius:40px;border:none;}");
            setChatStatus("Recognizing speech...");
            m_chatSession->setState(ChatState::AI_THINKING);
        }
    } else if (msg.startsWith("RECORD:READY")) {
        // could update UI; ignored for now
    }
}
