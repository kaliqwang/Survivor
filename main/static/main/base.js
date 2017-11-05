// ensures that buttons cannot spam multiple requests to server while waiting for a slow server response
$('.btn-long-resp').click(function(e) {
    if ($(this).hasClass('disabled')) {
        e.preventDefault();
    }
    $(this).addClass('disabled');
});