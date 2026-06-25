from __future__ import annotations

import logging
import os
import threading
import webbrowser
from pathlib import Path
from typing import Any

logger = logging.getLogger("bonfire.tray")

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
ICON_SVG = ASSETS_DIR / "bonfire.svg"

DAEMON_HOST = "127.0.0.1"
DAEMON_PORT = 21466

MENU_OPEN = 1
MENU_QUIT = 2


class TrayManager:
    def __init__(self, daemon: Any) -> None:
        self._daemon = daemon
        self._impl: Any = None
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        threading.Thread(target=self._run, daemon=True, name="tray").start()

    def stop(self) -> None:
        if self._impl is not None:
            self._impl.stop()
        self._impl = None

    def _run(self) -> None:
        if not ASSETS_DIR.is_dir() or not ICON_SVG.is_file():
            logger.warning("Assets not found — running headless")
            _url_fallback()
            return

        if _run_dbus_sni(self._daemon):
            return

        logger.info("D-Bus SNI unavailable, trying pystray")
        if _run_pystray(self._daemon):
            return

        logger.info("System tray unavailable — running headless")
        _url_fallback()


def _url_fallback() -> None:
    webbrowser.open(f"http://{DAEMON_HOST}:{DAEMON_PORT}")
    logger.info("Dashboard: http://%s:%d", DAEMON_HOST, DAEMON_PORT)


# ── pystray fallback ───────────────────────────────────────────────────────────

def _run_pystray(daemon: Any) -> bool:
    try:
        import pystray
        from PIL import Image

        img = Image.open(str(ICON_SVG)).resize((22, 22), Image.LANCZOS)
        menu = pystray.Menu(
            pystray.MenuItem("Open Dashboard", lambda: _url_fallback()),
            pystray.MenuItem("Quit", lambda icon, item: _pystray_quit(icon, daemon)),
        )
        icon = pystray.Icon("bonfire-client", img, "Bonfire", menu)
        icon.run()
        return True
    except ImportError:
        return False
    except Exception as e:
        logger.warning("pystray failed: %s", e)
        return False


def _pystray_quit(icon: Any, daemon: Any) -> None:
    icon.stop()
    threading.Thread(target=daemon.stop, daemon=True).start()


# ── D-Bus StatusNotifierItem via jeepney ──────────────────────────────────────

def _run_dbus_sni(daemon: Any) -> bool:
    try:
        from jeepney import DBusAddress
        from jeepney.io.blocking import open_dbus_connection, Proxy
    except ImportError:
        return False

    try:
        conn = open_dbus_connection(bus="SESSION")
    except Exception as e:
        logger.warning("Cannot connect to D-Bus session bus: %s", e)
        return False

    bus_name = f"org.kde.StatusNotifierItem-{os.getpid()}"

    try:
        bus_proxy = Proxy(
            DBusAddress(
                "/org/freedesktop/DBus",
                "org.freedesktop.DBus",
                "org.freedesktop.DBus",
            ),
            conn,
        )
        bus_proxy.RequestName(bus_name, 0)
    except Exception as e:
        logger.warning("Cannot request D-Bus name: %s", e)
        return False

    handler = _DBusSniHandler(conn, daemon)
    threading.Thread(target=handler._run, daemon=True, name="dbus-sni").start()

    try:
        watcher = Proxy(
            DBusAddress(
                "/StatusNotifierWatcher",
                "org.kde.StatusNotifierWatcher",
                "org.kde.StatusNotifierWatcher",
            ),
            conn,
        )
        watcher.RegisterStatusNotifierItem(bus_name)
        logger.info("D-Bus SNI registered as %s", bus_name)
        return True
    except Exception as e:
        logger.warning("Cannot register SNI: %s", e)
        return False


def _menu_item_variant(mid: int, label: str) -> Any:
    from jeepney.wrappers import Tuple, Variant, Array

    props = {
        "label": Variant("s", label),
        "enabled": Variant("b", True),
        "visible": Variant("b", True),
    }

    inner = Tuple(
        mid, props, Array([], signature="v"),
        signature="(ia{sv}av)",
    )
    return Variant("(ia{sv}av)", inner)


def _layout_tuple() -> Any:
    from jeepney.wrappers import Tuple, Array

    items = [
        _menu_item_variant(MENU_OPEN, "Open Dashboard"),
        _menu_item_variant(MENU_QUIT, "Quit"),
    ]

    return Tuple(
        0, {}, Array(items, signature="v"),
        signature="(ia{sv}av)",
    )


SNI_PROPS: dict[str, tuple[str, Any]] = {
    "Category": ("s", "ApplicationStatus"),
    "Id": ("s", "bonfire-client"),
    "Title": ("s", "Bonfire"),
    "Status": ("s", "Active"),
    "IconName": ("s", "bonfire"),
    "IconThemePath": ("s", str(ASSETS_DIR)),
    "IconPixmap": ("a(iiay)", []),
    "OverlayIconPixmap": ("a(iiay)", []),
    "AttentionIconPixmap": ("a(iiay)", []),
    "AttentionMovieName": ("s", ""),
    "ItemIsMenu": ("b", False),
    "WindowId": ("u", 0),
    "Menu": ("o", "/MenuBar"),
}


class _DBusSniHandler:
    def __init__(self, conn: Any, daemon: Any) -> None:
        self._conn = conn
        self._daemon = daemon
        self._running = True
        self._menu_revision = 0

    def stop(self) -> None:
        self._running = False

    def _run(self) -> None:
        from jeepney import MessageType, HeaderFields, new_method_return, new_error

        while self._running:
            try:
                msg = self._conn.recv(timeout=0.5)
            except TimeoutError:
                continue
            except Exception:
                if self._running:
                    logger.debug("D-Bus recv error", exc_info=True)
                continue

            if msg is None:
                continue
            if msg.header.message_type != MessageType.method_call:
                continue

            path = msg.header.fields.get(HeaderFields.path)
            iface = msg.header.fields.get(HeaderFields.interface)
            method = msg.header.fields.get(HeaderFields.member)

            try:
                if path == b"/StatusNotifierItem":
                    if iface == b"org.freedesktop.DBus.Properties":
                        self._handle_properties(msg, method)
                    elif iface == b"org.kde.StatusNotifierItem":
                        _url_fallback()
                        self._reply_empty(msg)
                elif path == b"/MenuBar":
                    if iface == b"com.canonical.dbusmenu":
                        self._handle_dbusmenu(msg, method)
            except Exception as e:
                logger.debug("D-Bus method error: %s", e)
                try:
                    self._conn.send(
                        new_error(
                            msg,
                            "org.freedesktop.DBus.Error.Failed",
                            str(e),
                        )
                    )
                except Exception:
                    pass

    def _reply(self, msg: Any, signature: str, *args: Any) -> None:
        from jeepney import new_method_return

        reply = new_method_return(msg, signature, *args)
        try:
            self._conn.send(reply)
        except Exception as e:
            logger.debug("Failed to send reply: %s", e)

    def _reply_empty(self, msg: Any) -> None:
        from jeepney import new_method_return

        try:
            self._conn.send(new_method_return(msg, "", ()))
        except Exception:
            pass

    def _handle_properties(self, msg: Any, method: bytes) -> None:
        from jeepney import new_error
        from jeepney.wrappers import Variant

        if method == b"Get":
            _prop = str(msg.body[1])
            entry = SNI_PROPS.get(_prop)
            if entry is not None:
                sig, val = entry
                self._reply(msg, "v", Variant((sig, val)))
            else:
                try:
                    self._conn.send(
                        new_error(msg, "org.freedesktop.DBus.Error.InvalidArgs", f"Unknown: {_prop}")
                    )
                except Exception:
                    pass
        elif method == b"GetAll":
            props = {}
            for key, (sig, val) in SNI_PROPS.items():
                props[key] = Variant((sig, val))
            self._reply(msg, "a{sv}", props)
        elif method == b"Set":
            try:
                self._conn.send(
                    new_error(msg, "org.freedesktop.DBus.Error.NotSupported", "Read-only")
                )
            except Exception:
                pass

    def _handle_dbusmenu(self, msg: Any, method: bytes) -> None:
        if method == b"GetLayout":
            self._reply(msg, "u(ia{sv}av)", self._menu_revision, _layout_tuple())

        elif method == b"GetGroupProperties":
            from jeepney.wrappers import Tuple, Variant

            ids = msg.body[0] if msg.body else []
            results = []
            for mid in ids:
                if mid in (MENU_OPEN, MENU_QUIT):
                    results.append(
                        Tuple(
                            mid,
                            {"enabled": Variant("b", True), "visible": Variant("b", True)},
                            signature="(ia{sv})",
                        )
                    )
            self._reply(msg, "a(ia{sv})", results)

        elif method == b"Event":
            _id = msg.body[0]
            event_id = msg.body[1]
            self._reply_empty(msg)
            if event_id == "clicked":
                if _id == MENU_OPEN:
                    _url_fallback()
                elif _id == MENU_QUIT:
                    threading.Thread(target=self._daemon.stop, daemon=True).start()

        elif method == b"EventClicked":
            _id = msg.body[0]
            self._reply_empty(msg)
            if _id == MENU_OPEN:
                _url_fallback()
            elif _id == MENU_QUIT:
                threading.Thread(target=self._daemon.stop, daemon=True).start()

        elif method in (b"AboutToShow", b"AboutToShowGroup"):
            self._reply(msg, "b", False)

        else:
            self._reply_empty(msg)
