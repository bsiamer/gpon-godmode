package com.gpon.godmode;

/**
 * Standard runtime exception thrown by GponClient operations when communication,
 * authentication, command execution, or parsing fails.
 */
public class GponException extends RuntimeException {

    private final int statusCode;

    public GponException(String message) {
        super(message);
        this.statusCode = 0;
    }

    public GponException(String message, Throwable cause) {
        super(message, cause);
        this.statusCode = 0;
    }

    public GponException(String message, int statusCode) {
        super(message + " (HTTP " + statusCode + ")");
        this.statusCode = statusCode;
    }

    public GponException(String message, Throwable cause, int statusCode) {
        super(message + " (HTTP " + statusCode + ")", cause);
        this.statusCode = statusCode;
    }

    /**
     * Gets the HTTP status code if the exception resulted from an HTTP response, or 0 otherwise.
     */
    public int getStatusCode() {
        return statusCode;
    }

    /**
     * Whether this exception originated from an HTTP error response.
     */
    public boolean isHttpError() {
        return statusCode > 0;
    }
}
