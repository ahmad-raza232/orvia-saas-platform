import { useState, useEffect, useRef } from 'react';
import { searchLocations } from '../utils/pakistanLocations';

const FreeLocationAutocomplete = ({ 
  label, 
  value, 
  onChange, 
  onLocationSelect,
  error,
  placeholder = 'Search city or area in Pakistan...',
  disabled = false,
  required = false
}) => {
  const isControlled = value !== undefined;
  const [internalValue, setInternalValue] = useState(value || '');
  const inputValue = isControlled ? value : internalValue;
  const [suggestions, setSuggestions] = useState([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const [isSearching, setIsSearching] = useState(false);
  const wrapperRef = useRef(null);
  const inputRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setShowDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Search locations when input changes
  useEffect(() => {
    const performSearch = () => {
      if (inputValue.length < 2) {
        setSuggestions([]);
        setShowDropdown(false);
        setIsSearching(false);
        return;
      }

      setIsSearching(true);
      
      // Simulate API delay for better UX
      setTimeout(() => {
        const results = searchLocations(inputValue);
        setSuggestions(results);
        setShowDropdown(results.length > 0);
        setIsSearching(false);
      }, 100);
    };

    const debounceTimer = setTimeout(performSearch, 300);
    return () => clearTimeout(debounceTimer);
  }, [inputValue]);

  const handleInputChange = (e) => {
    const newValue = e.target.value;
    if (!isControlled) {
      setInternalValue(newValue);
    }
    onChange?.(newValue);
    setSelectedIndex(-1);
  };

  const handleSelectSuggestion = (suggestion) => {
    const displayText = suggestion.displayText;
    if (!isControlled) {
      setInternalValue(displayText);
    }
    setShowDropdown(false);
    onChange?.(displayText);

    if (onLocationSelect) {
      onLocationSelect({
        province: suggestion.province,
        city: suggestion.city,
        area: suggestion.area,
        formattedAddress: suggestion.fullAddress,
        displayText: suggestion.displayText
      });
    }
  };

  const handleKeyDown = (e) => {
    if (!showDropdown || suggestions.length === 0) return;

    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setSelectedIndex(prev => 
          prev < suggestions.length - 1 ? prev + 1 : prev
        );
        break;
      case 'ArrowUp':
        e.preventDefault();
        setSelectedIndex(prev => prev > 0 ? prev - 1 : -1);
        break;
      case 'Enter':
        e.preventDefault();
        if (selectedIndex >= 0) {
          handleSelectSuggestion(suggestions[selectedIndex]);
        }
        break;
      case 'Escape':
        setShowDropdown(false);
        setSelectedIndex(-1);
        break;
      default:
        break;
    }
  };

  const handleClear = () => {
    if (!isControlled) {
      setInternalValue('');
    }
    onChange?.('');
    setSuggestions([]);
    setShowDropdown(false);
    onLocationSelect?.(null);
    inputRef.current?.focus();
  };

  return (
    <div ref={wrapperRef} className="relative w-full">
      {label && (
        <label className="mb-1.5 block text-sm font-semibold text-ink">
          {label} {required && <span className="text-danger">*</span>}
        </label>
      )}
      
      <div className="relative">
        <div className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-muted">
          <span className="sr-only">Location</span>
        </div>
        
        <input
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={handleInputChange}
          onKeyDown={handleKeyDown}
          onFocus={() => {
            if (inputValue.length >= 2 && suggestions.length > 0) {
              setShowDropdown(true);
            }
          }}
          placeholder={placeholder}
          disabled={disabled}
          className={`w-full rounded-md border bg-surface py-3 pl-4 pr-10 text-ink focus:outline-none focus:ring-4 focus:ring-olive/15 disabled:cursor-not-allowed disabled:opacity-50 ${
            error ? 'border-danger' : 'border-line focus:border-olive'
          }`}
        />
        
        {isSearching && (
          <div className="absolute right-3 top-1/2 -translate-y-1/2">
            <div className="h-5 w-5 animate-spin rounded-full border-2 border-olive/20 border-t-olive"></div>
          </div>
        )}

        {!isSearching && inputValue && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-muted hover:text-ink"
          >
            ×
          </button>
        )}
      </div>

      {error && (
        <p className="mt-1.5 text-sm text-danger">{error}</p>
      )}

      {/* Suggestions Dropdown */}
      {showDropdown && suggestions.length > 0 && (
        <div className="absolute z-50 mt-1 max-h-60 w-full overflow-y-auto rounded-md border border-line bg-surface shadow-sm">
          {suggestions.map((suggestion, index) => (
            <div
              key={`${suggestion.province}-${suggestion.city}-${suggestion.area || 'city'}-${index}`}
              onClick={() => handleSelectSuggestion(suggestion)}
              onMouseEnter={() => setSelectedIndex(index)}
              className={`cursor-pointer px-4 py-3 transition-colors ${
                index === selectedIndex
                  ? 'bg-olive text-peach'
                  : 'text-ink hover:bg-muted'
              }`}
            >
              <div className="min-w-0 flex-1">
                <div className="truncate font-medium">
                  {suggestion.city}
                  {suggestion.area && (
                    <span className={`ml-2 text-sm font-normal ${
                      index === selectedIndex ? 'text-peach/80' : 'text-ink-muted'
                    }`}>
                      {suggestion.area}
                    </span>
                  )}
                </div>
                <div className={`truncate text-sm ${
                  index === selectedIndex ? 'text-peach/80' : 'text-ink-muted'
                }`}>
                  {suggestion.province}, Pakistan
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* No results message */}
      {showDropdown && inputValue.length >= 2 && suggestions.length === 0 && !isSearching && (
        <div className="absolute z-50 mt-1 w-full rounded-md border border-line bg-surface p-4 shadow-sm">
          <div className="text-center text-ink-muted">
            <p className="text-sm">No locations found for "{inputValue}"</p>
            <p className="mt-1 text-xs">Try searching for a city or area name</p>
          </div>
        </div>
      )}

      {/* Helper text */}
      <p className="mt-1 text-xs text-ink-muted">
        Search for cities like Lahore, Karachi or areas like DHA, Gulberg
      </p>
    </div>
  );
};

export default FreeLocationAutocomplete;
