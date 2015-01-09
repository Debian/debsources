/* Copyright (C) 2014  Jason Pleau <jason@jpleau.ca>
 *
 * This file is part of Debsources.
 *
 * Debsources is free software: you can redistribute it and/or modify it under
 * the terms of the GNU Affero General Public License as published by the Free
 * Software Foundation, either version 3 of the License, or (at your option)
 * any later version.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License
 * for more details.
 *
 * You should have received a copy of the GNU Affero General Public License
 * along with this program.  If not, see <https://www.gnu.org/licenses/>.
 */

/*
 * Highlight line numbers according to data received in the anchor
 *
 * Example: file.cpp#L50-L275 will highlight lines 50 to 275.
 *
 * There's also support to select one line or a range of lines (by clicking on
 * a line or shift-clicking on a range of lines). The URL will be updated with
 * the selection.
 *
 */

var debsources = function(message_pos) {
    var print_lines = function() {
        var position = message_pos;
        var msgbox = document.getElementById('messages');
        var index = document.getElementById('sourceslinenumbers');
        var divHeight = msgbox.offsetHeight;
        var lineHeight = parseInt(window.getComputedStyle(index).getPropertyValue('line-height'),10);
        var lines = Math.ceil(divHeight / lineHeight)+1; // always insert one more line below the last line of code

        for(i=0; i<lines; ++i){
            var element = document.createElement('a');
            var s = '<a></a><br>'; // lines corr. messages do no need indexes
            element.innerHTML = s;
            var refnode = document.getElementById('L'+position.toString());
            refnode.parentNode.insertBefore(element,refnode.nextSibling);} //insert after the node with assigned position
    };

    function highlight_lines(start, end) {
        // First, remove the highlight class from elements that might already have it
        var elements = document.querySelectorAll("span.highlight");
        for (i = 0; i < elements.length; ++i) {
            var element = elements[i];
            element.className = element.className.replace(/\bhighlight\b/, '');
        }

        // Then, add the highlight class to elements that contain the lines we want to highlight
        for (i = start; i <= end; ++i) {
            var element = document.getElementById("line" + i);
            element.className = element.className + " highlight ";
        }
    }

    var hash_changed = function(event, scroll) {

        event = typeof event !== 'undefined' ? event: null;
        scroll = typeof scroll !== 'undefined' ? scroll: false;

        // Will match strings like #L15 and #L15-L20
        var regex = /#L(\d+)(-L(\d+))*$/;

        var match = regex.exec(window.location.hash);
        if (match != null) {
            var first_line = second_line = null;
            first_line = parseInt(match[1]);

            if (typeof match[3] !== 'undefined' && match[3].length > 0) {
                second_line = parseInt(match[3]);
            } else {
                second_line = first_line;
            }

            // If we get something like #L20-L15, just swap the two line numbers so the loop will work
            if (second_line < first_line) {
                var tmp = first_line;
                first_line = second_line;
                second_line = tmp;
            }

            highlight_lines(first_line, second_line);

            if (scroll) {
                window.scroll(0, document.getElementById("L"+first_line).offsetTop);
            }
        }
    };


    function change_hash_without_scroll(element, hash) {
        // This is necessary because when changing window.location.hash, the window will
        // scroll to the element's id if it matches the hash
        var id = element.id;
        element.id = id+'-tmpNoScroll';
        window.location.hash = hash;
        element.id = id;
    }

    var last_clicked;
    var line_click_handler = function(event) {
        if (event.preventDefault) {
            event.preventDefault();
        } else {
            event.returnValue = false;
        }

        var callerElement = event.target || event.srcElement;

        if (!event.shiftKey || !last_clicked) {
            last_clicked = callerElement;
            change_hash_without_scroll(callerElement, "L" + (callerElement.textContent || callerElement.innerText));
        } else {
            var first_line = parseInt(last_clicked.textContent || last_clicked.innerText);
            var second_line = parseInt(callerElement.textContent || callerElement.innerText);

            if (second_line < first_line) {
                var tmp = first_line;
                first_line = second_line;
                second_line = tmp;
            }

            change_hash_without_scroll(callerElement, "L" + first_line + "-L" + second_line);
        }
    };

    var window_load_sourcecode = function(event) {
        var line_numbers = document.querySelectorAll("#sourceslinenumbers a");
        for (i = 0; i < line_numbers.length; ++i) {
            var line_number_element = line_numbers[i];
            if (line_number_element.addEventListener) {
                line_number_element.addEventListener('click', line_click_handler, false);
            } else {
                line_number_element.attachEvent('onclick',  line_click_handler);
            }
        }
        hash_changed(null, true);
    };

    if (window.addEventListener) {
        window.addEventListener('load', window_load_sourcecode, false);
    } else {
        window.attachEvent('onload', window_load_sourcecode);
    }

    window.onhashchange = hash_changed;
    window.onload = print_lines;
};
