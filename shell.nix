{ pkgs ? import <nixpkgs> {} }:

# System packages needed to run tests with Qt, which requires
let
  libs = with pkgs; [
    # OpenGL
    libGL
    libglvnd

    # Fonts & text
    fontconfig
    freetype

    # System
    dbus
    glib
    zlib
    stdenv.cc.cc.lib

    # X11 / Qt platform
    xorg.libX11
    xorg.libXext
    xorg.libXrender
    xorg.libXrandr
    xorg.libXi
    xorg.libXcursor
    xorg.libXfixes
    xorg.libXcomposite
    xorg.libXdamage
    xorg.libxcb
    xorg.xcbutilcursor
    xorg.xcbutilimage
    xorg.xcbutilkeysyms
    xorg.xcbutilrenderutil
    xorg.xcbutilwm
    libxkbcommon
  ];
in
pkgs.mkShell {
  packages = with pkgs; [
    uv
    python311
    go-task

    # Include qttools for lrelease, lupdate commands
    qt6.qttools
  ];

  LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath libs;

  shellHook = ''
    # Headless Qt for unit tests (no display needed)
    export QT_QPA_PLATFORM=offscreen
  '';
}
