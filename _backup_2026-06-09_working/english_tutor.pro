QT += widgets gui opengl
QT += network
TARGET = english_tutor

RKNN_INC = /home/mjw/qsm_software/rk3568_linux_r60_v1.3.2_qsm368zp_d/buildroot/output/rockchip_rk3568/build/rknpu2-1.0.0/runtime/RK356X/Linux/librknn_api/include
RKNN_LIB = /home/mjw/qsm_software/rk3568_linux_r60_v1.3.2_qsm368zp_d/buildroot/output/rockchip_rk3568/build/rknpu2-1.0.0/runtime/RK356X/Linux/librknn_api/aarch64

INCLUDEPATH += $$RKNN_INC
LIBS += -L$$RKNN_LIB -lrknn_api

SOURCES += \
    main.cpp \
    AiCloudClient.cpp \
    ai_engine.cpp \
    postprocess.cpp \
    mainwindow.cpp \
    camerawidget.cpp \
    uart_client.cpp \
    action_manager.cpp \
    study_session_manager.cpp \
    pet_emotion.cpp \
    chat_session.cpp

HEADERS += \
    mainwindow.h \
    AiCloudClient.h \
    ai_engine.h \
    postprocess.h \
    camerawidget.h \
    uart_client.h \
    action_manager.h \
    study_session_manager.h \
    pet_emotion.h \
    chat_session.h
