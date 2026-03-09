from unittest.mock import MagicMock, patch
from vimlayer.hint_overlay import HintOverlay


def test_volume_up(mocker):
    # Mock subprocess.run
    mock_run = mocker.patch("subprocess.run")
    # Mock _get_volume_status to return 50%
    mocker.patch.object(HintOverlay, "_get_volume_status", return_value=(50, False))
    # Mock AppHelper.callAfter to call immediately
    mocker.patch("vimlayer.hint_overlay.AppHelper.callAfter", side_effect=lambda f, *args: f(*args))
    
    # We need to mock several things to initialize HintOverlay
    mocker.patch("vimlayer.hint_overlay.WatermarkManager")
    mocker.patch("vimlayer.hint_overlay.CheatSheetOverlay")
    mocker.patch("vimlayer.hint_overlay.WindowManager")
    mocker.patch("vimlayer.hint_overlay.Launcher")
    mocker.patch("vimlayer.hint_overlay.MouseController")
    
    overlay = HintOverlay()
    overlay.volume_up()
    
    # Verify osascript call
    mock_run.assert_called_with(
        ["osascript", "-e", "set volume output volume (output volume of (get volume settings) + 6)"]
    )
    # Verify watermark update
    overlay._watermark.set_mode.assert_called_with("VOL 50%")


def test_volume_mute_watermark(mocker):
    # Mock subprocess.run
    mock_run = mocker.patch("subprocess.run")
    # Mock _get_volume_status to return muted
    mocker.patch.object(HintOverlay, "_get_volume_status", return_value=(50, True))
    # Mock AppHelper.callAfter to call immediately
    mocker.patch("vimlayer.hint_overlay.AppHelper.callAfter", side_effect=lambda f, *args: f(*args))
    
    mocker.patch("vimlayer.hint_overlay.WatermarkManager")
    mocker.patch("vimlayer.hint_overlay.CheatSheetOverlay")
    mocker.patch("vimlayer.hint_overlay.WindowManager")
    mocker.patch("vimlayer.hint_overlay.Launcher")
    mocker.patch("vimlayer.hint_overlay.MouseController")
    
    overlay = HintOverlay()
    overlay.volume_mute()
    
    # Verify watermark update for muted
    overlay._watermark.set_mode.assert_called_with("VOL: MUTED")


def test_get_volume_status_parsing(mocker):
    # Mock subprocess.run to return expected osascript output
    mock_output = MagicMock()
    mock_output.stdout = "output volume:56, input volume:50, alert volume:100, output muted:false\n"
    mocker.patch("subprocess.run", return_value=mock_output)
    
    mocker.patch("vimlayer.hint_overlay.WatermarkManager")
    mocker.patch("vimlayer.hint_overlay.CheatSheetOverlay")
    mocker.patch("vimlayer.hint_overlay.WindowManager")
    mocker.patch("vimlayer.hint_overlay.Launcher")
    mocker.patch("vimlayer.hint_overlay.MouseController")
    
    overlay = HintOverlay()
    vol, muted = overlay._get_volume_status()
    
    assert vol == 56
    assert muted is False
