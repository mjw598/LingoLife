#include <QApplication>
#include <QScreen>
#include <QSurfaceFormat>
#include <QFontDatabase>
#include <QFont>
#include <cstdlib>
#include "mainwindow.h"

int main(int argc, char *argv[])
{
    // If weston/wayland is running, use wayland platform to avoid DRM conflict.
    // Otherwise fall back to eglfs for direct display access.
    if (qgetenv("WAYLAND_DISPLAY").isEmpty()) {
        qputenv("QT_QPA_PLATFORM", "eglfs");
        qputenv("QT_QPA_EGLFS_ALWAYS_SET_MODE", "1");
        qputenv("QT_QPA_EGLFS_HIDECURSOR", "1");
        qputenv("QT_QPA_EGLFS_INTEGRATION", "eglfs_kms");
    } else {
        qputenv("QT_QPA_PLATFORM", "wayland");
    }

    QApplication app(argc, argv);

    QFontDatabase::addApplicationFont("/data/fonts/NotoColorEmoji.ttf");
    QFontDatabase::addApplicationFont("/data/fonts/NotoEmoji-Regular.ttf");
    int fontId = QFontDatabase::addApplicationFont("/data/fonts/NotoSansCJK.ttc");
    if (fontId >= 0) {
        QStringList families = QFontDatabase::applicationFontFamilies(fontId);
        if (!families.isEmpty()) {
            QFont f(families.first());
            f.setStyleStrategy(QFont::PreferAntialias);
            app.setFont(f);
        }
    }

    QSurfaceFormat fmt;
    fmt.setRenderableType(QSurfaceFormat::OpenGL);
    fmt.setProfile(QSurfaceFormat::CoreProfile);
    fmt.setVersion(2, 0);
    QSurfaceFormat::setDefaultFormat(fmt);

    MainWindow w;
    w.setWindowTitle("AI English Tutor");
    w.showFullScreen();

    return app.exec();
}
