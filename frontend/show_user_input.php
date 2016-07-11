<?php
	//pretty print user_input.json
	if (file_exists("./user_input.json")) {
		$user_input = file_get_contents("./user_input.json");
		$user_input = json_decode($user_input, true);

		echo "<pre>";
		print_r($user_input);
		echo "</pre>";
	}
	else {
		echo "empty";
	}

?>