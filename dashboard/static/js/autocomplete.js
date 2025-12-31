/**
 * Professional Searchable Autocomplete with jQuery + AJAX
 * Reusable implementation with debounce and floating dropdown
 */

function initAutocomplete(inputSelector, endpointUrl) {
    const $input = $(inputSelector);
    if (!$input.length) {
        console.warn(`Autocomplete: Input selector "${inputSelector}" not found`);
        return;
    }

    // Create unique dropdown container
    const dropdownId = 'autocomplete-dropdown-' + Math.random().toString(36).substr(2, 9);
    const $dropdown = $(`
        <div id="${dropdownId}" class="autocomplete-dropdown" style="display: none;">
            <div class="autocomplete-loading" style="display: none;">
                <i class="bi bi-hourglass-split"></i> Searching...
            </div>
            <ul class="autocomplete-results"></ul>
        </div>
    `);

    // Insert dropdown after input
    $input.after($dropdown);

    // Debounce variables
    let debounceTimer = null;
    let currentRequest = null;

    // Position dropdown function
    function positionDropdown() {
        const inputOffset = $input.offset();
        const inputHeight = $input.outerHeight();
        const inputWidth = $input.outerWidth();

        $dropdown.css({
            position: 'absolute',
            top: inputOffset.top + inputHeight,
            left: inputOffset.left,
            width: inputWidth,
            zIndex: 1000
        });
    }

    // Show loading state
    function showLoading() {
        $dropdown.find('.autocomplete-loading').show();
        $dropdown.find('.autocomplete-results').hide();
        $dropdown.show();
        positionDropdown();
    }

    // Hide loading state
    function hideLoading() {
        $dropdown.find('.autocomplete-loading').hide();
    }

    // Hide dropdown
    function hideDropdown() {
        $dropdown.hide();
        hideLoading();
    }

    // Populate results
    function populateResults(results) {
        hideLoading();
        const $resultsList = $dropdown.find('.autocomplete-results');
        $resultsList.empty();

        if (!results || results.length === 0) {
            $resultsList.append('<li class="autocomplete-no-results">No results found</li>');
        } else {
            results.forEach(function(item) {
                const displayText = item.display_text || item.name || item.customer_name || 'Unknown';
                const $item = $(`<li class="autocomplete-item" data-id="${item.id}">${displayText}</li>`);
                $resultsList.append($item);
            });
        }

        $dropdown.find('.autocomplete-results').show();
        $dropdown.show();
        positionDropdown();
    }

    // Perform AJAX search
    function performSearch(query) {
        // Cancel previous request
        if (currentRequest) {
            currentRequest.abort();
        }

        showLoading();

        currentRequest = $.ajax({
            url: endpointUrl,
            method: 'GET',
            data: { q: query },
            dataType: 'json',
            success: function(response) {
                currentRequest = null;
                if (response.success) {
                    populateResults(response.customers || response.results || response.data || []);
                } else {
                    populateResults([]);
                }
            },
            error: function(xhr) {
                currentRequest = null;
                if (xhr.statusText !== 'abort') {
                    console.error('Autocomplete search failed:', xhr);
                    hideDropdown();
                }
            }
        });
    }

    // Input event handler with debounce
    $input.on('input', function() {
        const query = $(this).val().trim();

        // Clear debounce timer
        if (debounceTimer) {
            clearTimeout(debounceTimer);
        }

        // Cancel current request
        if (currentRequest) {
            currentRequest.abort();
            currentRequest = null;
        }

        if (query.length < 2) {
            hideDropdown();
            return;
        }

        // Set debounce timer (300ms)
        debounceTimer = setTimeout(function() {
            performSearch(query);
        }, 300);
    });

    // Click handler for results
    $dropdown.on('click', '.autocomplete-item', function() {
        const selectedText = $(this).text();
        const selectedId = $(this).data('id');

        // Fill input with selected value
        $input.val(selectedText);

        // Store selected ID in data attribute
        $input.data('selected-id', selectedId);

        // Hide dropdown immediately
        hideDropdown();

        // Trigger custom event
        $input.trigger('autocomplete:select', [selectedId, selectedText]);
    });

    // Hide dropdown when clicking outside
    $(document).on('click', function(e) {
        if (!$input.is(e.target) && !$dropdown.is(e.target) && $dropdown.has(e.target).length === 0) {
            hideDropdown();
        }
    });

    // Hide dropdown on escape key
    $input.on('keydown', function(e) {
        if (e.key === 'Escape') {
            hideDropdown();
        }
    });

    // Reposition on window resize
    $(window).on('resize', function() {
        if ($dropdown.is(':visible')) {
            positionDropdown();
        }
    });

    // Clear selected ID when input is manually changed
    $input.on('input', function() {
        $input.removeData('selected-id');
    });

    console.log(`Autocomplete initialized for "${inputSelector}" with endpoint "${endpointUrl}"`);
}