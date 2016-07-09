<?php
	// stores input passed though $_GET to file called user.input.json along with timestamp and user IP
	// 9.7.2016

	// trim and encode special characters for sanitazion
	$text = htmlspecialchars($_GET["user_input"]);
	$text = stripslashes($text);
	$text = trim($text, "\n\r");
	$time = date("j.n.Y H:i:s");
	// store user's IP address for logginf purposes
	$addr = $_SERVER["REMOTE_ADDR"];

	// check if user_input.json already exists
	if (file_exists("./user_input.json")) {
		// read previous data from file
		$user_input = file_get_contents("./user_input.json");
		$user_input = json_decode($user_input, true);

		// add new data to $user_input
		array_push($user_input["entry"], $text);
		array_push($user_input["timestamp"], $time);
		array_push($user_input["ip"], $addr);

		// write back to file
		file_put_contents("./user_input.json", json_encode($user_input));
	}
	// create new file with the user submitted data
	else {
		$data = array("entry" => array($text), "timestamp" => array($time), "ip" => array($addr));
		file_put_contents("./user_input.json", json_encode($data));
	}

	echo "Data submitted. You'll be happy to know this didn't actually do anything just yet. Check back later."
?>