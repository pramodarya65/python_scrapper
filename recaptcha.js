var system = require("system");
var webpage = require("webpage");

function wait(func, callback, timeoutFunc, retries) {
    var waitStatus = func();

    if (waitStatus != false) {
        callback(waitStatus);
    } else {
        if ((typeof(timeoutFunc) == "undefined") | (retries > 0)) {
            setTimeout(function() {
                if (typeof(timeoutFunc) != "undefined") {
                    wait(func, callback, timeoutFunc, retries - 1);
                } else {
                    wait(func, callback);
                }
            }, 1000);
        } else {
            writeLine("OPERATION TIMED OUT, RETRYING");
            timeoutFunc();
        }
    }
}

function writeLine(text) {
    system.stdout.writeLine(text);
    system.stdout.flush();
}

function readLine() {
    if (system.stdin.atEnd()) {
        phantom.exit();
    }

    return system.stdin.readLine();
}

var page = webpage.create();
page.settings.userAgent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/66.0.3359.117 Safari/537.36";
page.viewportSize = {width: 1280, height: 720};

page.open("https://www.ahu.go.id/pencarian/profil-pt", function(status) {
    wait(function() {
        return page.evaluate(function() {
            return document.querySelector("#g-recaptcha-response") != null;
        });
    }, function() {
        var recaptcha = page.evaluate(function() {
            return {
                key: document.querySelector(".g-recaptcha").getAttribute("data-sitekey"),
                url: window.location.href
            }
        });

        writeLine("recaptcha");
        writeLine(recaptcha.key);
        writeLine(recaptcha.url);

        var recaptchaResult = readLine();

        page.evaluate(function(recaptchaResult) {
            document.querySelector("#nama").value = "a  1";
            document.querySelector("#g-recaptcha-response").innerHTML = recaptchaResult;
            document.querySelector("#admin-ubah-form").submit();
        }, recaptchaResult);

        wait(function() {
            return page.evaluate(function() {
                return document.querySelector("#hasil_cari") != null;
            });
        }, function() {
            writeLine("success");
            writeLine(JSON.stringify({"cookies": phantom.cookies}));
            phantom.exit();
        });
    });
});
