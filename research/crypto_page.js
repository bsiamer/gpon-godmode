
((sjcl.beware && sjcl.beware["CBC mode is dangerous because it doesn't protect message integrity."]) ||
  function(){})();

var crypto_page = (function() {

    var base64url_escape = function(b64) {
        var out = "";
        for(i = 0; i < b64.length; i++) {
            var c = b64.charAt(i);
            if (c == '+') {
                out += '-';
            } else if (c == '/') {
                out += '_';
            } else if (c == '=') {
                out += '.';
            } else {
                out += c;
            }
        }
        return out;
    };

    var encrypt = function(pubkey, plaintext) {
        var aeskey = sjcl.random.randomWords(4, 0);
        var iv = sjcl.random.randomWords(4, 0);
        var pt = sjcl.codec.utf8String.toBits(plaintext);
        var aes = new sjcl.cipher.aes(aeskey);
        var ct = sjcl.mode.cbc.encrypt(aes, pt, iv);
        
        var rsa = new JSEncrypt(); 
        if(rsa.setPublicKey(pubkey) == false)
            return fasle;

        var base64url = sjcl.codec.base64url;
        var base64 = sjcl.codec.base64;
        var aesinfo = base64.fromBits(aeskey) + ' ' + base64.fromBits(iv);
        var ck = rsa.encrypt(aesinfo);
        if(ck == false)
            return false;

        return {
            ct:base64url.fromBits(ct),
            ck:base64url_escape(ck)
        };
    };

    var aes_decrypt = function(sid, ciphertext) {
        var keyinfo = localStorage.getItem(sid);
        if(keyinfo && ciphertext.length > 0)
        {
            var key_iv = keyinfo.split(' ');
            var key = sjcl.codec.base64.toBits(key_iv[0]);
            var iv = sjcl.codec.base64.toBits(key_iv[1]);
            var ct = sjcl.codec.base64.toBits(ciphertext);
            var aes = new sjcl.cipher.aes(key);
            try{
                var pt = sjcl.mode.cbc.decrypt(aes, ct, iv);
                return sjcl.codec.utf8String.fromBits(pt);
            }catch(err) {
                console.log(err.message);
            }
        }

        return ciphertext;
    };


    var encrypt_post_data = function(pubkey, plaintext) {
        var p = encrypt(pubkey, plaintext);
        return  'encrypted=1&ct=' + p.ct + '&ck=' + p.ck;
    };

    var sha256 = function(val1, val2) {
        var out = sjcl.hash.sha256.hash(val1 + ":" + val2);
        return sjcl.codec.base64.fromBits(out);
    };

    var sha256url = function(val1, val2) {
        return base64url_escape(sha256(val1, val2));
    }

    return {
        encrypt : encrypt,
        encrypt_post_data: encrypt_post_data,
        sha256: sha256,
        sha256url: sha256url,
        base64url_escape: base64url_escape,
        aes_decrypt : aes_decrypt
    }
})();

var login_page = (function() {

    var submit = function(info) {
        var a1 = crypto_page.sha256(info.username, info.password);
        var response  = crypto_page.sha256url(a1, info.nonce);
        var userhash = crypto_page.sha256url(info.username, info.nonce);
        var postdata = 'userhash=' + userhash + '&response=' + response + '&nonce=' + crypto_page.base64url_escape(info.nonce);

        var base64 = sjcl.codec.base64;
        var dec_key = base64.fromBits(sjcl.random.randomWords(4, 0));
        var dec_iv = base64.fromBits(sjcl.random.randomWords(4, 0));

        postdata += '&enckey=' + crypto_page.base64url_escape(dec_key);  
        postdata += '&enciv=' + crypto_page.base64url_escape(dec_iv);  

        if(info.encrypt) {
            postdata = crypto_page.encrypt_post_data(info.pubkey, postdata);
        }

        $.ajax({                        
                url: info.url,
                type: 'POST',
                data: postdata,
                success: function(data, textstatus, jqXHR) {
                    if (jqXHR.status == 299) {
                        var sid = jqXHR.getResponseHeader('X-SID');

                        localStorage.clear();
                        localStorage.setItem(sid, dec_key + ' ' + dec_iv);
                        window.top.location="/"
                    }
                    else {
                        var doc = document.open("text/html", "replace");
                        doc.write(data);
                        doc.close();
                    }
                }
            });

    }


    return {
        submit:submit
    }
})();
