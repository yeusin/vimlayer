import sys
from unittest.mock import MagicMock
import pytest
import os
from vimlayer.accessibility import (
    _is_element_covered,
    _score_element,
    search,
)


def test_is_element_covered(mocker):
    # Element coordinates
    ex, ey, ew, eh = 100, 100, 50, 50
    pid = 1234
    
    # Target window is in the win_list
    target_wid = 10

    # Win list with some windows
    win_list = [
        {
            "kCGWindowNumber": 20,
            "kCGWindowOwnerPID": 5678,
            "kCGWindowLayer": 0,
            "kCGWindowBounds": {"X": 0, "Y": 0, "Width": 1920, "Height": 1080}
        },
        {
            "kCGWindowNumber": 10,
            "kCGWindowOwnerPID": pid,
            "kCGWindowLayer": 0,
            "kCGWindowBounds": {"X": 50, "Y": 50, "Width": 500, "Height": 500}
        }
    ]
    
    # Mock os.getpid to return a different PID
    mocker.patch("os.getpid", return_value=9999)

    # In this case, window 20 (from another app) covers the element and is in front of window 10
    assert _is_element_covered(ex, ey, ew, eh, pid, win_list, target_wid) is True

    # If we put our target window in front, it shouldn't be covered
    win_list.reverse()
    assert _is_element_covered(ex, ey, ew, eh, pid, win_list, target_wid) is False


def test_score_element():
    el = {
        "role": "AXButton",
        "subrole": "AXCloseButton",
        "title": "Close",
        "description": "",
        "value": "",
        "clickable": True,
    }

    # Semantic match
    assert _score_element(el, "close", ("AXButton", "AXCloseButton")) == 100

    # Prefix match
    assert _score_element(el, "cl", None) > 0
    
    # Non match
    assert _score_element(el, "xyz", None) == 0


def test_search():
    elements = [
        {
            "role": "AXButton",
            "subrole": "AXCloseButton",
            "title": "Close Window",
            "description": "",
            "value": "",
            "clickable": True,
        },
        {
            "role": "AXButton",
            "subrole": "",
            "title": "Submit",
            "description": "",
            "value": "",
            "clickable": True,
        }
    ]

    # Search for "close"
    results = search("close", elements)
    assert len(results) == 1
    assert results[0]["title"] == "Close Window"
    
    # Empty query returns all
    assert len(search("", elements)) == 2
