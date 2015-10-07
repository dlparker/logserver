(function() {
    $(document).on('ready', function() {
        var form1 = $('#form1');
        var button1 = $(form1).find('button');
        var form2 = $('#form2');
        var button2 = $(form2).find('button');
        button2.prop('disabled', true);
        var form3 = $('#form3');
        var button3 = $(form3).find('button');
        button3.prop('disabled', true);
        var caller_data = {
	    platform:'browser',
            version: 'value',
            token: Date().toString(),
	    'app_id': 'control_panel_direct_input'
        }

        function setupButton1() {
            button1.on('click', function(e) {
                e.preventDefault();
                $.ajax({
                    url: '/get_logging_url',
                    dataType: 'json',
                    data: caller_data,
                    success: function (response) {
                        //alert('got logging url ' + response.url);
                        window.logging_url = response.url
                        $('#logging_url').html(response.url)
                        button2.prop('disabled', false);
                    },
                    error: function (xhr, ajaxOptions, thrownError) {
                        alert(xhr.status);
                        alert(thrownError);
                    }
                });
            });
        }

        function setupButton2() {
            button2.on('click', function(e) {
                e.preventDefault();
                $.ajax({
                    url: window.logging_url + 'get_new_stream_id',
                    dataType: 'json',
                    data: caller_data,
                    success: function (response) {
                        //alert('got stream id ' + response.id);
                        $('#stream_id').html(response.id)
                        window.logging_stream_id = response.id
                        button3.prop('disabled', false);
                    },
                    error: function (xhr, ajaxOptions, thrownError) {
                        alert(xhr.status);
                        alert(thrownError);
                    }
                });
            });
        }
        function setupButton3() {
            var logger = $(form3).find('#logger');
            var level = $(form3).find('#level');
            var message = $(form3).find('#message');
            button3.on('click', function(e) {
                e.preventDefault();
                var data = {
                    data: JSON.stringify([{
                        timestamp: new Date().getTime(),
                        logger: logger.attr('value'),
                        level: level.attr('value'),
                        message: message.attr('value')
                    }])
                }
                $.ajax({
                    type: 'POST',
                    url: window.logging_url + 'stream/' + window.logging_stream_id + '/record',
                    dataType: 'json',
                    data: data,
                    success: function (response) {
                        //alert('got record response ' + JSON.stringify(response));
                        $('#messages').append(JSON.stringify(response) + "</br>");
                    },
                    error: function (xhr, ajaxOptions, thrownError) {
                        alert(xhr.status);
                        alert(thrownError);
                    }
                });
            });
        }
        setupButton1();
        setupButton2();
        setupButton3();
    });
})()
