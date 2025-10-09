/**
 * WebAuthn Passkey Client
 * Handles passkey registration and authentication
 */

/**
 * Convert base64url to ArrayBuffer
 */
function base64urlToBuffer(base64url) {
    const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/');
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
}

/**
 * Convert ArrayBuffer to base64url
 */
function bufferToBase64url(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    const base64 = btoa(binary);
    return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

/**
 * Register a new passkey
 */
async function registerPasskey(deviceName = 'My Device') {
    try {
        // Begin registration
        const beginResponse = await fetch('/passkey/register-begin', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ device_name: deviceName })
        });

        if (!beginResponse.ok) {
            throw new Error('Failed to begin registration');
        }

        const options = await beginResponse.json();

        // Convert base64url strings to ArrayBuffers
        options.challenge = base64urlToBuffer(options.challenge);
        options.user.id = base64urlToBuffer(options.user.id);

        if (options.excludeCredentials) {
            options.excludeCredentials = options.excludeCredentials.map(cred => ({
                ...cred,
                id: base64urlToBuffer(cred.id)
            }));
        }

        // Create the credential
        const credential = await navigator.credentials.create({
            publicKey: options
        });

        if (!credential) {
            throw new Error('Failed to create credential');
        }

        // Convert ArrayBuffers to base64url for transmission
        const attestationResponse = {
            id: credential.id,
            rawId: bufferToBase64url(credential.rawId),
            type: credential.type,
            response: {
                clientDataJSON: bufferToBase64url(credential.response.clientDataJSON),
                attestationObject: bufferToBase64url(credential.response.attestationObject),
            }
        };

        // Complete registration
        const completeResponse = await fetch('/passkey/register-complete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(attestationResponse)
        });

        if (!completeResponse.ok) {
            const error = await completeResponse.json();
            throw new Error(error.error || 'Failed to complete registration');
        }

        const result = await completeResponse.json();
        return result;

    } catch (error) {
        console.error('Passkey registration error:', error);
        throw error;
    }
}

/**
 * Authenticate with a passkey
 */
async function authenticateWithPasskey() {
    try {
        // Begin authentication
        const beginResponse = await fetch('/passkey/login-begin', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (!beginResponse.ok) {
            throw new Error('Failed to begin authentication');
        }

        const options = await beginResponse.json();

        // Convert base64url strings to ArrayBuffers
        options.challenge = base64urlToBuffer(options.challenge);

        if (options.allowCredentials) {
            options.allowCredentials = options.allowCredentials.map(cred => ({
                ...cred,
                id: base64urlToBuffer(cred.id)
            }));
        }

        // Get the credential
        const credential = await navigator.credentials.get({
            publicKey: options
        });

        if (!credential) {
            throw new Error('Failed to get credential');
        }

        // Convert ArrayBuffers to base64url for transmission
        const assertionResponse = {
            id: credential.id,
            rawId: bufferToBase64url(credential.rawId),
            type: credential.type,
            response: {
                clientDataJSON: bufferToBase64url(credential.response.clientDataJSON),
                authenticatorData: bufferToBase64url(credential.response.authenticatorData),
                signature: bufferToBase64url(credential.response.signature),
                userHandle: credential.response.userHandle ? bufferToBase64url(credential.response.userHandle) : null,
            }
        };

        // Complete authentication
        const completeResponse = await fetch('/passkey/login-complete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(assertionResponse)
        });

        if (!completeResponse.ok) {
            const error = await completeResponse.json();
            throw new Error(error.error || 'Failed to complete authentication');
        }

        const result = await completeResponse.json();
        return result;

    } catch (error) {
        console.error('Passkey authentication error:', error);
        throw error;
    }
}

/**
 * Check if WebAuthn is supported
 */
function isPasskeySupported() {
    return window.PublicKeyCredential !== undefined &&
           navigator.credentials !== undefined;
}

/**
 * List user's passkeys
 */
async function listPasskeys() {
    try {
        const response = await fetch('/passkey/list');
        if (!response.ok) {
            throw new Error('Failed to list passkeys');
        }
        return await response.json();
    } catch (error) {
        console.error('List passkeys error:', error);
        throw error;
    }
}

/**
 * Delete a passkey
 */
async function deletePasskey(passkeyId) {
    try {
        const response = await fetch(`/passkey/delete/${passkeyId}`, {
            method: 'DELETE'
        });
        if (!response.ok) {
            throw new Error('Failed to delete passkey');
        }
        return await response.json();
    } catch (error) {
        console.error('Delete passkey error:', error);
        throw error;
    }
}

// Export functions
window.passkey = {
    register: registerPasskey,
    authenticate: authenticateWithPasskey,
    isSupported: isPasskeySupported,
    list: listPasskeys,
    delete: deletePasskey
};
