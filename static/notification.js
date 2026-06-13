const notificationBtn =
document.querySelector(".notification-btn");

const notificationDropdown =
document.querySelector(".notification-dropdown");

if(notificationBtn && notificationDropdown){

    notificationBtn.addEventListener(
        "click",
        function(e){

            e.stopPropagation();

            notificationDropdown.classList.toggle("show");

            if(notificationDropdown.classList.contains("show")){

                fetch("/mark_notifications_read")
                .catch(error => {
                    console.log(
                        "Notification error:",
                        error
                    );
                });

                const badge =
                document.querySelector(
                    ".notification-count"
                );

                if(badge){
                    badge.innerHTML = "";
                }

            }

        }
    );

    document.addEventListener(
        "click",
        function(){

            notificationDropdown.classList.remove(
                "show"
            );

        }
    );

}